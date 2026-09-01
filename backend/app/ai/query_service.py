"""The allow-listed, deterministic query toolset the AI layer is built
on top of — every function here is a plain SQLAlchemy query against
already-known tables/columns, never AI-generated SQL, never a raw
prompt handed to a database. Each function returns a plain dict:
{"answer": str, "results": [...], "resource_ids": [...]} — a
human-readable deterministic answer, a list of small structured result
rows (for a UI table/cards), and the list of record IDs actually
touched (for the AI audit log). None of this depends on an AI provider
being configured at all; this module has no AI imports."""

from datetime import timedelta

from ..campaigns.service import campaign_progress
from ..extensions import db
from ..models import (
    Activity, ActivityParticipant, AssistanceRequest, Campaign, ElderlyMember,
    EXPENSE_COUNTED_STATUSES, Expense, HomeVisit, Incident, InventoryItem, Program,
    User, VolunteerAvailability, VolunteerHours, VolunteerProfile, utcnow,
)

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _today():
    return utcnow().date()


def visits_today():
    today = _today()
    visits = (
        HomeVisit.query.filter(db.func.date(HomeVisit.scheduled_at) == today.isoformat())
        .order_by(HomeVisit.scheduled_at.asc())
        .all()
    )
    results = [
        {"id": v.id, "member_name": v.elderly_member.full_name, "status": v.status, "scheduled_at": v.scheduled_at.isoformat() if v.scheduled_at else None, "assigned_to": v.assigned_to.name if v.assigned_to else None}
        for v in visits
    ]
    answer = f"{len(visits)} home visit(s) scheduled today." if visits else "No home visits are scheduled today."
    return {"answer": answer, "results": results, "resource_ids": [v.id for v in visits]}


def unassigned_requests():
    requests = (
        AssistanceRequest.query.filter(AssistanceRequest.assigned_to_id.is_(None), AssistanceRequest.status.notin_(("Completed", "Cancelled")))
        .order_by(AssistanceRequest.created_at.asc())
        .all()
    )
    results = [
        {"id": r.id, "member_name": r.elderly_member.full_name, "request_type": r.request_type, "priority": r.priority, "status": r.status}
        for r in requests
    ]
    answer = f"{len(requests)} assistance request(s) are currently unassigned." if requests else "No assistance requests are currently unassigned."
    return {"answer": answer, "results": results, "resource_ids": [r.id for r in requests]}


def overdue_concerns(min_days_open=3, high_priority_only=False):
    today = utcnow()
    query = Incident.query.filter(Incident.status.in_(("Open", "Under Review")))
    if high_priority_only:
        query = query.filter(Incident.severity.in_(("Critical", "High")))
    incidents = query.order_by(Incident.occurred_at.asc()).all()

    overdue = []
    for incident in incidents:
        days_open = (today.date() - incident.created_at.date()).days
        if days_open >= min_days_open:
            overdue.append((incident, days_open))

    results = [
        {"id": i.id, "member_name": i.elderly_member.full_name if i.elderly_member else None, "incident_type": i.incident_type, "severity": i.severity, "status": i.status, "days_open": days}
        for i, days in overdue
    ]
    label = "high-priority " if high_priority_only else ""
    answer = f"{len(overdue)} {label}concern(s) have been open {min_days_open}+ days." if overdue else f"No {label}concerns have been open {min_days_open}+ days."
    return {"answer": answer, "results": results, "resource_ids": [i.id for i, _ in overdue]}


def volunteer_availability(day_of_week=None):
    query = (
        db.session.query(VolunteerProfile)
        .join(User, VolunteerProfile.user_id == User.id)
        .filter(VolunteerProfile.status == "Verified")
    )
    if day_of_week:
        query = query.join(VolunteerAvailability, VolunteerAvailability.volunteer_profile_id == VolunteerProfile.id).filter(VolunteerAvailability.day_of_week == day_of_week)
    profiles = query.distinct().order_by(User.name.asc()).all()

    results = [{"volunteer_id": p.user_id, "name": p.user.name} for p in profiles]
    scope = f" on {day_of_week}" if day_of_week else ""
    answer = f"{len(profiles)} verified volunteer(s) available{scope}." if profiles else f"No verified volunteers have availability recorded{scope}."
    return {"answer": answer, "results": results, "resource_ids": [p.user_id for p in profiles]}


def members_without_recent_visits(days=30):
    cutoff = _today() - timedelta(days=days)
    members = ElderlyMember.query.filter(ElderlyMember.status == "Active").all()

    flagged = []
    for member in members:
        last_visit = (
            HomeVisit.query.filter_by(elderly_member_id=member.id, status="Completed")
            .order_by(HomeVisit.completed_at.desc())
            .first()
        )
        last_date = last_visit.completed_at.date() if last_visit and last_visit.completed_at else None
        if last_date is None or last_date < cutoff:
            flagged.append((member, last_date))

    results = [
        {"id": m.id, "member_name": m.full_name, "member_code": m.member_id, "last_visit_date": ld.isoformat() if ld else None}
        for m, ld in flagged
    ]
    answer = f"{len(flagged)} active member(s) have had no completed visit in the last {days} days." if flagged else f"Every active member has had a completed visit within the last {days} days."
    return {"answer": answer, "results": results, "resource_ids": [m.id for m, _ in flagged]}


def program_attendance(period_days=30, limit=10):
    since = _today() - timedelta(days=period_days)
    rows = (
        db.session.query(Program.id, Program.name, db.func.count(ActivityParticipant.id))
        .join(Activity, Activity.program_id == Program.id)
        .join(ActivityParticipant, ActivityParticipant.activity_id == Activity.id)
        .filter(ActivityParticipant.status == "Attended", ActivityParticipant.updated_at >= since)
        .group_by(Program.id, Program.name)
        .order_by(db.func.count(ActivityParticipant.id).desc())
        .limit(limit)
        .all()
    )
    results = [{"program_id": pid, "program_name": name, "attendance_count": count} for pid, name, count in rows]
    answer = f"Top program by attendance in the last {period_days} days: {results[0]['program_name']} ({results[0]['attendance_count']})." if results else f"No recorded program attendance in the last {period_days} days."
    return {"answer": answer, "results": results, "resource_ids": [r["program_id"] for r in results]}


def finance_summary(program_name=None, period_days=30):
    since = _today() - timedelta(days=period_days)
    query = Expense.query.filter(Expense.status.in_(EXPENSE_COUNTED_STATUSES), Expense.expense_date >= since)
    matched_program = None
    if program_name:
        matched_program = Program.query.filter(Program.name.ilike(f"%{program_name}%")).first()
        if matched_program is None:
            return {"answer": f'No program matching "{program_name}" was found.', "results": [], "resource_ids": []}
        query = query.filter(Expense.program_id == matched_program.id)

    total = query.with_entities(db.func.coalesce(db.func.sum(Expense.amount), 0)).scalar()
    expenses = query.order_by(Expense.expense_date.desc()).limit(20).all()
    results = [{"id": e.id, "program_name": e.program.name if e.program else None, "amount": float(e.amount), "category": e.category, "expense_date": e.expense_date.isoformat()} for e in expenses]

    scope = f" by {matched_program.name}" if matched_program else " across all programs"
    answer = f"KES {float(total):,.2f} spent{scope} in the last {period_days} days."
    return {"answer": answer, "results": results, "resource_ids": [e.id for e in expenses]}


def campaigns_below_threshold(percent=50):
    campaigns = Campaign.query.filter(Campaign.status == "Active").all()
    flagged = []
    for campaign in campaigns:
        progress = campaign_progress(campaign, recent_limit=0)
        if progress["percent_achieved"] < percent:
            flagged.append((campaign, progress))

    results = [
        {"id": c.id, "name": c.name, "percent_achieved": p["percent_achieved"], "raised_amount": p["raised_amount"], "goal_amount": p["goal_amount"]}
        for c, p in flagged
    ]
    answer = f"{len(flagged)} active campaign(s) are below {percent}% of their goal." if flagged else f"Every active campaign has reached at least {percent}% of its goal."
    return {"answer": answer, "results": results, "resource_ids": [c.id for c, _ in flagged]}


def inventory_low_stock():
    items = InventoryItem.query.filter(InventoryItem.current_stock <= InventoryItem.minimum_stock).order_by(InventoryItem.name.asc()).all()
    results = [{"id": i.id, "name": i.name, "current_stock": float(i.current_stock), "minimum_stock": float(i.minimum_stock), "unit": i.unit} for i in items]
    answer = f"{len(items)} inventory item(s) are at or below their minimum stock level." if items else "No inventory items are currently low on stock."
    return {"answer": answer, "results": results, "resource_ids": [i.id for i in items]}


def volunteer_hours_leaderboard(period_days=90, limit=5):
    since = _today() - timedelta(days=period_days)
    rows = (
        db.session.query(VolunteerProfile.user_id, User.name, db.func.coalesce(db.func.sum(VolunteerHours.duration_minutes), 0))
        .join(User, VolunteerProfile.user_id == User.id)
        .join(VolunteerHours, VolunteerHours.volunteer_profile_id == VolunteerProfile.id)
        .filter(VolunteerHours.status == "Approved", VolunteerHours.date >= since)
        .group_by(VolunteerProfile.user_id, User.name)
        .order_by(db.func.sum(VolunteerHours.duration_minutes).desc())
        .limit(limit)
        .all()
    )
    results = [{"volunteer_id": uid, "name": name, "hours": round(minutes / 60, 1)} for uid, name, minutes in rows]
    answer = f"Top volunteer by service hours in the last {period_days} days: {results[0]['name']} ({results[0]['hours']}h)." if results else f"No approved volunteer hours recorded in the last {period_days} days."
    return {"answer": answer, "results": results, "resource_ids": [r["volunteer_id"] for r in results]}


def operational_risk_summary():
    """A composite of the sharpest-edged checks above, for "summarize
    today's operational risks" — deliberately reuses the same functions
    rather than re-querying, so this can never drift from what each
    individual intent would report on its own."""
    high_priority = overdue_concerns(min_days_open=0, high_priority_only=True)
    unassigned = unassigned_requests()
    low_stock = inventory_low_stock()
    stale_members = members_without_recent_visits(days=30)

    risk_count = len(high_priority["results"]) + len(unassigned["results"]) + len(low_stock["results"])
    if risk_count == 0:
        answer = "No notable operational risks right now."
    else:
        parts = []
        if high_priority["results"]:
            parts.append(f"{len(high_priority['results'])} high-priority concern(s) open")
        if unassigned["results"]:
            parts.append(f"{len(unassigned['results'])} unassigned request(s)")
        if low_stock["results"]:
            parts.append(f"{len(low_stock['results'])} low-stock item(s)")
        answer = "; ".join(parts) + "."

    resource_ids = high_priority["resource_ids"] + unassigned["resource_ids"] + low_stock["resource_ids"]
    return {
        "answer": answer,
        "results": {
            "high_priority_concerns": high_priority["results"],
            "unassigned_requests": unassigned["results"],
            "low_stock_items": low_stock["results"],
            "members_without_recent_visits": stale_members["results"],
        },
        "resource_ids": resource_ids,
    }


# ---------- Volunteer-scoped (self-only) ----------

def volunteer_my_schedule(user_id):
    today = _today()
    visits = HomeVisit.query.filter(HomeVisit.assigned_to_id == user_id, db.func.date(HomeVisit.scheduled_at) == today.isoformat()).order_by(HomeVisit.scheduled_at.asc()).all()
    requests = AssistanceRequest.query.filter(AssistanceRequest.assigned_to_id == user_id, db.func.date(AssistanceRequest.scheduled_at) == today.isoformat()).order_by(AssistanceRequest.scheduled_at.asc()).all()

    results = (
        [{"id": v.id, "type": "home_visit", "member_name": v.elderly_member.full_name, "scheduled_at": v.scheduled_at.isoformat() if v.scheduled_at else None, "status": v.status} for v in visits]
        + [{"id": r.id, "type": "assistance_request", "member_name": r.elderly_member.full_name, "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None, "status": r.status} for r in requests]
    )
    total = len(visits) + len(requests)
    answer = f"You have {total} assignment(s) scheduled today." if total else "You have nothing scheduled today."
    return {"answer": answer, "results": results, "resource_ids": [v.id for v in visits] + [r.id for r in requests]}


def volunteer_my_hours(user_id, period_days=30):
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        return {"answer": "No volunteer profile found.", "results": [], "resource_ids": []}
    since = _today() - timedelta(days=period_days)
    minutes = db.session.query(db.func.coalesce(db.func.sum(VolunteerHours.duration_minutes), 0)).filter(
        VolunteerHours.volunteer_profile_id == profile.id, VolunteerHours.status == "Approved", VolunteerHours.date >= since,
    ).scalar()
    hours = round(minutes / 60, 1)
    answer = f"You've logged {hours} approved hour(s) in the last {period_days} days."
    return {"answer": answer, "results": [{"hours": hours, "period_days": period_days}], "resource_ids": [profile.id]}


def volunteer_my_training(user_id):
    from ..models import TrainingCourse, TrainingProgress

    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        return {"answer": "No volunteer profile found.", "results": [], "resource_ids": []}

    required_courses = TrainingCourse.query.filter_by(required=True, active=True).all()
    completed_ids = {
        p.course_id for p in TrainingProgress.query.filter_by(volunteer_profile_id=profile.id, status="Completed").all()
    }
    outstanding = [c for c in required_courses if c.id not in completed_ids]

    results = [{"id": c.id, "title": c.title, "category": c.category} for c in outstanding]
    answer = f"You have {len(outstanding)} required training item(s) still to complete." if outstanding else "You're up to date on all required training."
    return {"answer": answer, "results": results, "resource_ids": [c.id for c in outstanding]}


def volunteer_my_messages(user_id):
    from ..models import Conversation, DirectMessage

    conversations = Conversation.query.filter(db.or_(Conversation.user_one_id == user_id, Conversation.user_two_id == user_id)).all()
    unread = 0
    for conversation in conversations:
        read_at = conversation.read_at_for(user_id)
        message_query = DirectMessage.query.filter(
            DirectMessage.conversation_id == conversation.id, DirectMessage.sender_id != user_id,
        )
        if read_at:
            message_query = message_query.filter(DirectMessage.created_at > read_at)
        unread += message_query.count()
    answer = f"You have {unread} unread message(s)." if unread else "You have no unread messages."
    return {"answer": answer, "results": [{"unread_count": unread}], "resource_ids": []}
