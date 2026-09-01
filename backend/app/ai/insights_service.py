"""Deterministic workload analysis, trend detection, and smart
recommendations — no AI/ML anywhere in this module. Every number here
is computed directly from the database; the AI layer (see
ai/routes.py) only ever adds an optional narrative sentence on top of
what this module already decided."""

import statistics
from datetime import timedelta

from ..budgets.service import budget_spent, budget_warning_level
from ..extensions import db
from ..matching.service import ACTIVE_STATUSES as ASSIGNMENT_ACTIVE_STATUSES
from ..models import (
    Activity, ACTIVITY_VOLUNTEER_CONFIRMED_STATUSES, ActivityVolunteer, AssistanceRequest, Budget,
    Document, FollowUp, HomeVisit, Incident, TrainingCourse, TrainingProgress, User, VolunteerHours,
    VolunteerProfile, utcnow,
)

REQUEST_UNASSIGNED_STALE_DAYS = 2
CONCERN_STALE_DAYS = 3
NO_SHOW_THRESHOLD = 2
DOCUMENT_EXPIRY_WINDOW_DAYS = 30


def _today():
    return utcnow().date()


# ---------- Workload ----------

def _active_assignment_counts():
    counts = {}
    for profile in VolunteerProfile.query.filter_by(status="Verified").all():
        visit_count = HomeVisit.query.filter(HomeVisit.assigned_to_id == profile.user_id, HomeVisit.status.in_(ASSIGNMENT_ACTIVE_STATUSES)).count()
        request_count = AssistanceRequest.query.filter(AssistanceRequest.assigned_to_id == profile.user_id, AssistanceRequest.status.in_(ASSIGNMENT_ACTIVE_STATUSES)).count()
        counts[profile.user_id] = visit_count + request_count
    return counts


def workload_insights():
    counts = _active_assignment_counts()
    median = statistics.median(counts.values()) if counts else 0

    overloaded, idle = [], []
    for user_id, count in counts.items():
        user = db.session.get(User, user_id)
        if median > 0 and count > 2 * median:
            overloaded.append({"volunteer_id": user_id, "name": user.name, "active_count": count})
        if count == 0:
            idle.append({"volunteer_id": user_id, "name": user.name})

    since = _today() - timedelta(days=90)
    no_show_rows = (
        db.session.query(ActivityVolunteer.volunteer_id, db.func.count(ActivityVolunteer.id))
        .filter(ActivityVolunteer.status == "No Show", ActivityVolunteer.updated_at >= since)
        .group_by(ActivityVolunteer.volunteer_id)
        .all()
    )
    high_no_show = [
        {"volunteer_id": uid, "name": db.session.get(User, uid).name, "no_show_count": count}
        for uid, count in no_show_rows if count >= NO_SHOW_THRESHOLD
    ]

    understaffed_activities = (
        Activity.query.filter(Activity.registration_open.is_(True), Activity.capacity.isnot(None), Activity.scheduled_at >= utcnow())
        .all()
    )
    understaffed = []
    for activity in understaffed_activities:
        confirmed = ActivityVolunteer.query.filter(ActivityVolunteer.activity_id == activity.id, ActivityVolunteer.status.in_(ACTIVITY_VOLUNTEER_CONFIRMED_STATUSES)).count()
        gap = activity.capacity - confirmed
        if gap > 0:
            understaffed.append({"activity_id": activity.id, "title": activity.title, "scheduled_at": activity.scheduled_at.isoformat(), "spots_short": gap})

    stale_cutoff = _today() - timedelta(days=CONCERN_STALE_DAYS)
    stale_concerns = Incident.query.filter(Incident.status.in_(("Open", "Under Review")), Incident.created_at < stale_cutoff).count()

    unassigned_cutoff = _today() - timedelta(days=REQUEST_UNASSIGNED_STALE_DAYS)
    stale_requests = AssistanceRequest.query.filter(
        AssistanceRequest.assigned_to_id.is_(None), AssistanceRequest.status.notin_(("Completed", "Cancelled")),
        AssistanceRequest.created_at < unassigned_cutoff,
    ).count()

    return {
        "median_active_assignments": median,
        "overloaded_volunteers": overloaded,
        "idle_volunteers": idle,
        "high_no_show_volunteers": high_no_show,
        "understaffed_programs": understaffed,
        "stale_concern_count": stale_concerns,
        "stale_unassigned_request_count": stale_requests,
    }


# ---------- Trend detection ----------

def _count_trend(query_builder, current_days):
    """query_builder(start, end) -> Query, filtered as [start, end) —
    used identically for the current and previous windows so the two
    counts are directly comparable. `end` for the CURRENT window is
    tomorrow (not today), so today's own activity — which is exactly
    what a same-day trend check needs to see — isn't excluded by the
    exclusive upper bound."""
    today = _today()
    tomorrow = today + timedelta(days=1)
    current_start = today - timedelta(days=current_days - 1)
    previous_start = current_start - timedelta(days=current_days)

    current = query_builder(current_start, tomorrow).count()
    previous = query_builder(previous_start, current_start).count()
    return _trend_result(current, previous)


def _sum_trend(sum_builder, current_days):
    today = _today()
    tomorrow = today + timedelta(days=1)
    current_start = today - timedelta(days=current_days - 1)
    previous_start = current_start - timedelta(days=current_days)

    current = float(sum_builder(current_start, tomorrow) or 0)
    previous = float(sum_builder(previous_start, current_start) or 0)
    return _trend_result(current, previous)


def _trend_result(current, previous):
    if previous == 0:
        pct_change = 0.0 if current == 0 else 100.0
    else:
        pct_change = round((current - previous) / previous * 100, 1)
    direction = "up" if current > previous else "down" if current < previous else "flat"
    return {"current": current, "previous": previous, "pct_change": pct_change, "direction": direction}


def operational_trends(period_days=30):
    assistance_requests = _count_trend(
        lambda start, end: AssistanceRequest.query.filter(db.func.date(AssistanceRequest.created_at) >= start.isoformat(), db.func.date(AssistanceRequest.created_at) < end.isoformat()),
        period_days,
    )
    visit_completions = _count_trend(
        lambda start, end: HomeVisit.query.filter(HomeVisit.status == "Completed", db.func.date(HomeVisit.completed_at) >= start.isoformat(), db.func.date(HomeVisit.completed_at) < end.isoformat()),
        period_days,
    )
    concerns = _count_trend(
        lambda start, end: Incident.query.filter(db.func.date(Incident.created_at) >= start.isoformat(), db.func.date(Incident.created_at) < end.isoformat()),
        period_days,
    )
    volunteer_hours = _sum_trend(
        lambda start, end: db.session.query(db.func.sum(VolunteerHours.duration_minutes)).filter(
            VolunteerHours.status == "Approved", VolunteerHours.date >= start, VolunteerHours.date < end,
        ).scalar(),
        period_days,
    )

    return {
        "period_days": period_days,
        "assistance_requests": assistance_requests,
        "visit_completions": visit_completions,
        "concerns": concerns,
        "volunteer_hours_minutes": volunteer_hours,
    }


# ---------- Smart recommendations ----------

def smart_recommendations():
    recommendations = []

    workload = workload_insights()
    for program in workload["understaffed_programs"]:
        recommendations.append({
            "type": "program_staffing", "resource_type": "activity", "resource_id": program["activity_id"],
            "text": f"{program['title']} is short {program['spots_short']} volunteer(s).",
        })

    stale_visits = HomeVisit.query.filter(HomeVisit.follow_up_required.is_(True)).all()
    stale_requests = AssistanceRequest.query.filter(AssistanceRequest.follow_up_required.is_(True)).all()
    missing_follow_up = []
    for source_type, rows in (("home_visit", stale_visits), ("assistance_request", stale_requests)):
        for row in rows:
            has_open_follow_up = FollowUp.query.filter(
                FollowUp.source_type == source_type, FollowUp.source_id == row.id, FollowUp.status != "Completed",
            ).first() is not None
            if not has_open_follow_up:
                missing_follow_up.append({"source_type": source_type, "source_id": row.id})
    if missing_follow_up:
        recommendations.append({
            "type": "follow_up", "resource_type": "follow_up_gap", "resource_id": None,
            "text": f"{len(missing_follow_up)} record(s) marked follow-up required have no open follow-up task.",
            "detail": missing_follow_up[:20],
        })

    required_courses = TrainingCourse.query.filter_by(required=True, active=True).all()
    if required_courses:
        required_ids = {c.id for c in required_courses}
        verified_volunteers = VolunteerProfile.query.filter_by(status="Verified").all()
        gap_count = 0
        for profile in verified_volunteers:
            completed_ids = {p.course_id for p in TrainingProgress.query.filter_by(volunteer_profile_id=profile.id, status="Completed").all()}
            if required_ids - completed_ids:
                gap_count += 1
        if gap_count:
            recommendations.append({
                "type": "training_gap", "resource_type": "volunteer_profile", "resource_id": None,
                "text": f"{gap_count} verified volunteer(s) have not completed all required training.",
            })

    expiry_cutoff = _today() + timedelta(days=DOCUMENT_EXPIRY_WINDOW_DAYS)
    expiring_documents = Document.query.filter(
        Document.expiry_date.isnot(None), Document.expiry_date <= expiry_cutoff, Document.expiry_date >= _today(), Document.status == "Verified",
    ).all()
    if expiring_documents:
        recommendations.append({
            "type": "document_expiry", "resource_type": "document", "resource_id": None,
            "text": f"{len(expiring_documents)} document(s) expire within {DOCUMENT_EXPIRY_WINDOW_DAYS} days.",
            "detail": [{"id": d.id, "title": d.title, "expiry_date": d.expiry_date.isoformat()} for d in expiring_documents[:20]],
        })

    for budget in Budget.query.all():
        spent = budget_spent(budget)
        allocated = float(budget.allocated_amount)
        level = budget_warning_level(allocated, spent)
        if level in ("alert", "exceeded"):
            percent_used = round(spent / allocated * 100, 1) if allocated else 0
            recommendations.append({
                "type": "budget_alert", "resource_type": "budget", "resource_id": budget.id,
                "text": f"{budget.program.name} has used {percent_used}% of its budget.",
            })

    return {"recommendations": recommendations}
