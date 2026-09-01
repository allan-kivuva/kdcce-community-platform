"""Deterministic fact-gathering for the daily briefings — every number
here comes straight from the database. ai/routes.py hands these facts
to ai/service.py for an optional AI-written narrative; the AI is never
allowed to invent a metric that isn't already in this dict."""

from datetime import timedelta

from ..achievements.service import current_achievement_value
from ..extensions import db
from ..matching.service import ACTIVE_STATUSES as ASSIGNMENT_ACTIVE_STATUSES
from ..models import (
    Achievement, Activity, ActivityVolunteer, HomeVisit, User,
    VolunteerAchievement, VolunteerHours, VolunteerProfile, utcnow,
)
from . import insights_service, query_service

MEMBER_STALE_DAYS = 30


def _today():
    return utcnow().date()


def admin_daily_briefing():
    today = _today()
    yesterday = today - timedelta(days=1)

    visits_today = HomeVisit.query.filter(db.func.date(HomeVisit.scheduled_at) == today.isoformat()).count()
    unassigned = query_service.unassigned_requests()
    high_priority_concerns = query_service.overdue_concerns(min_days_open=0, high_priority_only=True)

    unconfirmed = ActivityVolunteer.query.join(Activity, ActivityVolunteer.activity_id == Activity.id).filter(
        ActivityVolunteer.status == "Assigned", db.func.date(Activity.scheduled_at) == today.isoformat(),
    ).count()
    events_today = Activity.query.filter(db.func.date(Activity.scheduled_at) == today.isoformat()).order_by(Activity.scheduled_at.asc()).all()

    stale_members = query_service.members_without_recent_visits(days=MEMBER_STALE_DAYS)
    stale_concerns = query_service.overdue_concerns(min_days_open=3)
    low_stock = query_service.inventory_low_stock()
    understaffed = insights_service.workload_insights()["understaffed_programs"]

    visits_completed_yesterday = HomeVisit.query.filter(HomeVisit.status == "Completed", db.func.date(HomeVisit.completed_at) == yesterday.isoformat()).count()
    achievements_yesterday = VolunteerAchievement.query.filter(db.func.date(VolunteerAchievement.awarded_at) == yesterday.isoformat()).count()

    facts = {
        "date": today.isoformat(),
        "today": {
            "visits_scheduled": visits_today,
            "unassigned_requests": len(unassigned["results"]),
            "high_priority_concerns_open": len(high_priority_concerns["results"]),
            "unconfirmed_assignments": unconfirmed,
            "events_today": [{"id": a.id, "title": a.title, "scheduled_at": a.scheduled_at.isoformat()} for a in events_today],
        },
        "needs_attention": {
            "members_without_recent_visits": stale_members["results"][:5],
            "stale_concerns": stale_concerns["results"][:5],
            "low_stock_items": low_stock["results"][:5],
            "understaffed_programs": understaffed[:5],
        },
        "recent_activity": {
            "visits_completed_yesterday": visits_completed_yesterday,
            "achievements_awarded_yesterday": achievements_yesterday,
        },
    }
    return facts, _render_admin_briefing_text(facts)


def _render_admin_briefing_text(facts):
    lines = ["GOOD MORNING", "", "TODAY"]
    t = facts["today"]
    lines.append(f"- {t['visits_scheduled']} home visit(s) scheduled")
    lines.append(f"- {t['unassigned_requests']} request(s) remain unassigned")
    lines.append(f"- {t['high_priority_concerns_open']} high-priority concern(s) are open")
    if t["unconfirmed_assignments"]:
        lines.append(f"- {t['unconfirmed_assignments']} volunteer assignment(s) have not been confirmed")
    for event in t["events_today"]:
        lines.append(f"- {event['title']} begins at {event['scheduled_at']}")

    n = facts["needs_attention"]
    has_attention_items = any(n.values())
    lines += ["", "NEEDS ATTENTION"]
    if not has_attention_items:
        lines.append("- Nothing notable — no overdue members, concerns, low stock, or understaffed programs right now.")
    else:
        for member in n["members_without_recent_visits"]:
            lines.append(f"- {member['member_name']} has had no visit in over {MEMBER_STALE_DAYS} days")
        for concern in n["stale_concerns"]:
            lines.append(f"- Concern #{concern['id']} has been open {concern['days_open']} day(s)")
        for item in n["low_stock_items"]:
            lines.append(f"- {item['name']} stock is below threshold ({item['current_stock']} {item['unit']})")
        for program in n["understaffed_programs"]:
            lines.append(f"- {program['title']} still needs {program['spots_short']} volunteer(s)")

    r = facts["recent_activity"]
    lines += ["", "RECENT ACTIVITY"]
    lines.append(f"- {r['visits_completed_yesterday']} visit(s) completed yesterday")
    lines.append(f"- {r['achievements_awarded_yesterday']} volunteer achievement(s) awarded yesterday")

    return "\n".join(lines)


def _next_milestone(user_id, profile_id):
    earned_ids = {va.achievement_id for va in VolunteerAchievement.query.filter_by(volunteer_profile_id=profile_id).all()}
    candidates = Achievement.query.filter_by(active=True).filter(Achievement.threshold_value.isnot(None)).all()
    best = None
    for achievement in candidates:
        if achievement.id in earned_ids:
            continue
        current = current_achievement_value(achievement.threshold_type, user_id, profile_id)
        remaining = achievement.threshold_value - current
        if remaining <= 0:
            continue
        if best is None or remaining < best["remaining"]:
            best = {"name": achievement.name, "threshold_type": achievement.threshold_type, "current": current, "remaining": remaining}
    return best


def volunteer_daily_briefing(user_id):
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    if profile is None:
        return {"error": "No volunteer profile found."}, "No volunteer profile found on this account."

    user = db.session.get(User, user_id)
    today = _today()
    month_start = today.replace(day=1)

    schedule = query_service.volunteer_my_schedule(user_id)
    messages = query_service.volunteer_my_messages(user_id)
    training = query_service.volunteer_my_training(user_id)

    minutes_this_month = db.session.query(db.func.coalesce(db.func.sum(VolunteerHours.duration_minutes), 0)).filter(
        VolunteerHours.volunteer_profile_id == profile.id, VolunteerHours.status == "Approved", VolunteerHours.date >= month_start,
    ).scalar()
    completed_visits_total = HomeVisit.query.filter(HomeVisit.assigned_to_id == user_id, HomeVisit.status == "Completed").count()
    achievement_count = VolunteerAchievement.query.filter_by(volunteer_profile_id=profile.id).count()

    milestone = _next_milestone(user_id, profile.id)

    facts = {
        "name": user.name,
        "today": {
            "assignment_count": len(schedule["results"]),
            "assignments": schedule["results"],
            "unread_messages": messages["results"][0]["unread_count"],
            "training_outstanding": len(training["results"]),
        },
        "impact": {
            "hours_this_month": round(minutes_this_month / 60, 1),
            "completed_visits_total": completed_visits_total,
            "achievement_count": achievement_count,
        },
        "next_milestone": milestone,
    }
    return facts, _render_volunteer_briefing_text(facts)


def _render_volunteer_briefing_text(facts):
    first_name = facts["name"].split(" ")[0]
    lines = [f"GOOD MORNING, {first_name.upper()}", "", "TODAY"]
    t = facts["today"]
    lines.append(f"- {t['assignment_count']} visit(s)/request(s) scheduled")
    for a in t["assignments"][:5]:
        lines.append(f"  - {a['member_name']} at {a['scheduled_at'] or 'an unscheduled time'}")
    lines.append(f"- {t['unread_messages']} new message(s)")
    if t["training_outstanding"]:
        lines.append(f"- {t['training_outstanding']} required training item(s) still due")

    lines += ["", "YOUR IMPACT"]
    i = facts["impact"]
    lines.append(f"- {i['hours_this_month']} hours this month")
    lines.append(f"- {i['completed_visits_total']} completed visits (all time)")
    lines.append(f"- {i['achievement_count']} achievement(s) earned")

    milestone = facts["next_milestone"]
    if milestone:
        lines += ["", "NEXT MILESTONE"]
        lines.append(f"- {milestone['remaining']} more toward \"{milestone['name']}\"")

    return "\n".join(lines)
