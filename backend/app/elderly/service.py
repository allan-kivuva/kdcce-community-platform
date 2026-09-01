from ..extensions import db
from ..models import (
    Attendance, AssignmentAttachment, AssistanceRequest, HealthRecord, HomeVisit, Incident,
    Meal, MealAttendance, Medication, MedicationAdministration,
)


def build_member_timeline_events(member_id):
    """Combines events from 7 existing modules into one chronological
    feed — deliberately NOT a new event table duplicating those records.
    Each module is already indexed on elderly_member_id and this is
    scoped to one person, so it's 7 fixed, cheap, already-indexed
    queries — not N+1 (N would be "one query per timeline row"; this is
    always exactly 7 regardless of how much history exists), and each
    query is filtered at the database, not loaded-then-filtered in
    Python. The one extra query (photo attachments) is a single
    IN-clause batch lookup, not one query per visit/request, to avoid
    turning that into real N+1.

    Extracted from elderly/routes.py:get_member_timeline() in Phase 9 so
    the AI member-timeline-summary feature (see ai/summary_service.py)
    can reuse the exact same aggregation instead of re-deriving it —
    both now call this one function, so they can never drift apart."""
    attendance = Attendance.query.filter_by(elderly_member_id=member_id).all()
    health = HealthRecord.query.filter_by(elderly_member_id=member_id).all()
    administrations = (
        db.session.query(MedicationAdministration, Medication.name)
        .join(Medication, MedicationAdministration.medication_id == Medication.id)
        .filter(Medication.elderly_member_id == member_id).all()
    )
    visits = HomeVisit.query.filter_by(elderly_member_id=member_id).all()
    requests_ = AssistanceRequest.query.filter_by(elderly_member_id=member_id).all()
    incidents = Incident.query.filter_by(elderly_member_id=member_id).all()
    meals = (
        db.session.query(MealAttendance, Meal.meal_type, Meal.meal_date)
        .join(Meal, MealAttendance.meal_id == Meal.id)
        .filter(MealAttendance.elderly_member_id == member_id).all()
    )

    photo_assignment_ids = {("home_visit", v.id) for v in visits} | {("assistance_request", r.id) for r in requests_}
    attachments = set()
    if photo_assignment_ids:
        rows = AssignmentAttachment.query.filter(
            db.tuple_(AssignmentAttachment.assignment_type, AssignmentAttachment.assignment_id).in_(photo_assignment_ids)
        ).all()
        attachments = {(a.assignment_type, a.assignment_id) for a in rows}

    events = []
    for a in attendance:
        events.append({
            "type": "attendance", "timestamp": a.check_in_at.isoformat(), "title": "Attendance",
            "details": {"check_in_at": a.check_in_at.isoformat(), "check_out_at": a.check_out_at.isoformat() if a.check_out_at else None, "notes": a.notes},
        })
    for h in health:
        events.append({
            "type": "health", "timestamp": h.recorded_at.isoformat(), "title": "Health Observation",
            "details": {
                "temperature_celsius": float(h.temperature_celsius) if h.temperature_celsius is not None else None,
                "mood": h.mood, "wellbeing": h.wellbeing, "observations": h.observations,
                "follow_up_required": h.follow_up_required,
            },
        })
    for m, medication_name in administrations:
        events.append({
            "type": "medication", "timestamp": m.administered_at.isoformat(), "title": "Medication",
            "details": {"medication_name": medication_name, "status": m.status, "notes": m.notes},
        })
    for v in visits:
        events.append({
            "type": "home_visit", "timestamp": v.created_at.isoformat(), "title": "Home Visit",
            "details": {
                "assigned_to": v.assigned_to.name if v.assigned_to else None, "status": v.status,
                "reason": v.reason, "observations": v.observations, "has_photo": ("home_visit", v.id) in attachments,
            },
        })
    for r in requests_:
        events.append({
            "type": "assistance", "timestamp": r.created_at.isoformat(), "title": f"Assistance — {r.request_type}",
            "details": {
                "assigned_to": r.assigned_to.name if r.assigned_to else None, "status": r.status,
                "description": r.description, "has_photo": ("assistance_request", r.id) in attachments,
            },
        })
    for i in incidents:
        events.append({
            "type": "incident", "timestamp": i.occurred_at.isoformat(), "title": f"Incident — {i.incident_type}",
            "details": {"severity": i.severity, "status": i.status, "description": i.description},
        })
    for ma, meal_type, meal_date in meals:
        events.append({
            "type": "meal", "timestamp": ma.created_at.isoformat(), "title": f"Feeding — {meal_type}",
            "details": {"meal_date": meal_date.isoformat(), "notes": ma.notes},
        })

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events
