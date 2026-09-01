"""Deterministic fact-gathering for concern (Incident) summaries and
elderly-member timeline summaries — admin/staff only for both (see
ai/routes.py). Data minimization is applied here, before anything is
ever handed to ai/service.py: only the fields each summary genuinely
needs are collected, nothing extraneous (no reporter contact info
beyond name, no unrelated member records, no raw uploaded file
content)."""

from datetime import timedelta

from ..elderly.service import build_member_timeline_events
from ..models import FollowUp, HomeVisit, Incident, utcnow

MAX_FOLLOW_UPS = 10
MAX_TIMELINE_EVENTS = 40


def gather_concern_facts(incident):
    """Everything an admin/staff user already has full access to via the
    existing incident endpoint — a concern summary is not a family-safe
    or reduced view, since only admin/staff can call this at all (see
    roles_required("admin","staff") in ai/routes.py)."""
    follow_ups = (
        FollowUp.query.filter_by(source_type="incident", source_id=incident.id)
        .order_by(FollowUp.created_at.asc())
        .limit(MAX_FOLLOW_UPS)
        .all()
    )
    related_visits = (
        HomeVisit.query.filter_by(elderly_member_id=incident.elderly_member_id)
        .filter(HomeVisit.created_at >= incident.occurred_at)
        .order_by(HomeVisit.created_at.asc())
        .limit(5)
        .all()
        if incident.elderly_member_id else []
    )

    facts = {
        "incident_id": incident.id,
        "member_name": incident.elderly_member.full_name if incident.elderly_member else None,
        "incident_type": incident.incident_type,
        "severity": incident.severity,
        "status": incident.status,
        "occurred_at": incident.occurred_at.isoformat(),
        "description": incident.description,
        "immediate_action_taken": incident.immediate_action_taken,
        "resolution_notes": incident.resolution_notes,
        "emergency_contact_notified": incident.emergency_contact_notified,
        "follow_up_history": [
            {"id": f.id, "status": f.status, "due_date": f.due_date.isoformat() if f.due_date else None, "reason": f.reason, "notes": f.notes, "created_at": f.created_at.isoformat()}
            for f in follow_ups
        ],
        "visits_since_incident": [
            {"id": v.id, "status": v.status, "scheduled_at": v.scheduled_at.isoformat() if v.scheduled_at else None}
            for v in related_visits
        ],
    }
    resource_ids = [incident.id] + [f.id for f in follow_ups] + [v.id for v in related_visits]
    return facts, resource_ids


def render_concern_summary_fallback(facts):
    parts = [f"Incident #{facts['incident_id']} ({facts['incident_type']}, {facts['severity']} severity) reported {facts['occurred_at'][:10]}."]
    if facts["description"]:
        parts.append(f"Description: {facts['description']}")
    if facts["follow_up_history"]:
        parts.append(f"{len(facts['follow_up_history'])} follow-up record(s) exist, most recent status: {facts['follow_up_history'][-1]['status']}.")
    if facts["visits_since_incident"]:
        parts.append(f"{len(facts['visits_since_incident'])} home visit(s) recorded since.")
    parts.append(f"Current status: {facts['status']}.")
    return " ".join(parts)


def gather_timeline_facts(member, days=30, since=None, until=None):
    """`days` is used unless an explicit (since, until) range is given —
    matching the 7/30/90-day presets plus a bounded custom range the
    Phase 9 brief calls for. Capped well below anything that would ever
    need to be batched into an AI prompt (MAX_TIMELINE_EVENTS)."""
    now = utcnow()
    if since is None:
        since = (now - timedelta(days=days)).date().isoformat()
    if until is None:
        until = now.date().isoformat()

    events = build_member_timeline_events(member.id)
    windowed = [e for e in events if since <= e["timestamp"][:10] <= until][:MAX_TIMELINE_EVENTS]

    counts = {}
    for event in windowed:
        counts[event["type"]] = counts.get(event["type"], 0) + 1

    facts = {
        "member_name": member.full_name,
        "since": since,
        "until": until,
        "event_counts": counts,
        "events": windowed,
    }
    resource_ids = [member.id]
    return facts, resource_ids


_TYPE_LABELS = {
    "home_visit": "home visit(s)", "assistance": "assistance request(s) touched", "incident": "concern(s) recorded",
    "meal": "feeding program attendance", "attendance": "day-program attendance", "health": "health observation(s)",
    "medication": "medication administration(s)",
}


def render_timeline_summary_fallback(facts):
    if not facts["event_counts"]:
        return f"No recorded activity for {facts['member_name']} between {facts['since']} and {facts['until']}."
    parts = [f"{count} {_TYPE_LABELS.get(t, t)}" for t, count in facts["event_counts"].items()]
    return f"Between {facts['since']} and {facts['until']}, {facts['member_name']} had: " + ", ".join(parts) + "."
