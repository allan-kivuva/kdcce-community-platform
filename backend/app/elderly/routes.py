from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import (
    OPA, AssignmentAttachment, AssistanceRequest, Attendance, ElderlyMember, HealthRecord, HomeVisit,
    Incident, Meal, MealAttendance, Medication, MedicationAdministration,
)
from ..utils import get_or_404, validation_error_response
from .schemas import OPASchema, ElderlyMemberSchema

bp = Blueprint("elderly", __name__)

opa_schema = OPASchema()
member_schema = ElderlyMemberSchema()


# ---------- OPAs (community groups) ----------

@bp.get("/api/opas")
@roles_required("admin", "staff")
def list_opas():
    opas = OPA.query.order_by(OPA.name.asc()).all()
    return jsonify(opas=[o.to_dict() for o in opas]), 200


@bp.post("/api/opas")
@roles_required("admin", "staff")
def create_opa():
    payload = request.get_json(silent=True) or {}
    try:
        data = opa_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    if OPA.query.filter_by(name=data["name"]).first():
        return jsonify(error="An OPA with that name already exists"), 409

    opa = OPA(**data)
    db.session.add(opa)
    db.session.commit()
    return jsonify(opa=opa.to_dict()), 201


@bp.patch("/api/opas/<int:opa_id>")
@roles_required("admin", "staff")
def update_opa(opa_id):
    opa = get_or_404(OPA, opa_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = opa_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    for field, value in data.items():
        setattr(opa, field, value)
    db.session.commit()
    return jsonify(opa=opa.to_dict()), 200


@bp.delete("/api/opas/<int:opa_id>")
@roles_required("admin", "staff")
def delete_opa(opa_id):
    opa = get_or_404(OPA, opa_id)
    db.session.delete(opa)
    db.session.commit()
    return "", 204


# ---------- Elderly members ----------

def _make_member_id(member):
    year = datetime.now(timezone.utc).year
    return f"KDCCE-{year}-{str(member.id).zfill(4)}"


@bp.get("/api/elderly")
@roles_required("admin", "staff")
def list_members():
    query = ElderlyMember.query
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(ElderlyMember.full_name.ilike(like), ElderlyMember.member_id.ilike(like)))
    status = request.args.get("status")
    if status:
        query = query.filter(ElderlyMember.status == status)
    opa_id = request.args.get("opa_id", type=int)
    if opa_id:
        query = query.filter(ElderlyMember.opa_id == opa_id)

    members = query.order_by(ElderlyMember.full_name.asc()).all()
    return jsonify(members=[m.to_dict() for m in members]), 200


@bp.get("/api/elderly/<int:member_id>")
@roles_required("admin", "staff")
def get_member(member_id):
    member = get_or_404(ElderlyMember, member_id)
    return jsonify(member=member.to_dict()), 200


@bp.get("/api/elderly/<int:member_id>/timeline")
@roles_required("admin", "staff")
def get_member_timeline(member_id):
    """Combines events from 7 existing modules into one chronological
    feed — deliberately NOT a new event table duplicating those records.
    Each module is already indexed on elderly_member_id and this is
    scoped to one person, so it's 7 fixed, cheap, already-indexed
    queries — not N+1 (N would be "one query per timeline row"; this is
    always exactly 7 regardless of how much history exists), and each
    query is filtered at the database, not loaded-then-filtered in
    Python. The one extra query (photo attachments) is a single
    IN-clause batch lookup, not one query per visit/request, to avoid
    turning that into real N+1."""
    member = get_or_404(ElderlyMember, member_id)

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

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    total = len(events)
    start = (page - 1) * per_page
    page_events = events[start:start + per_page]

    return jsonify(
        member=member.to_dict(),
        timeline=page_events,
        pagination={"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page if per_page else 0},
    ), 200


@bp.post("/api/elderly")
@roles_required("admin", "staff")
def create_member():
    payload = request.get_json(silent=True) or {}
    try:
        data = member_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    opa_id = data.get("opa_id")
    if opa_id is not None and db.session.get(OPA, opa_id) is None:
        return jsonify(error="Validation failed", details={"opa_id": ["OPA not found"]}), 400

    member = ElderlyMember(**data, member_id="")
    db.session.add(member)
    db.session.flush()  # assigns member.id without committing yet
    member.member_id = _make_member_id(member)
    db.session.commit()
    return jsonify(member=member.to_dict()), 201


@bp.patch("/api/elderly/<int:member_id>")
@roles_required("admin", "staff")
def update_member(member_id):
    member = get_or_404(ElderlyMember, member_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = member_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "opa_id" in data and data["opa_id"] is not None and db.session.get(OPA, data["opa_id"]) is None:
        return jsonify(error="Validation failed", details={"opa_id": ["OPA not found"]}), 400

    for field, value in data.items():
        setattr(member, field, value)
    db.session.commit()
    return jsonify(member=member.to_dict()), 200


@bp.delete("/api/elderly/<int:member_id>")
@roles_required("admin")
def delete_member(member_id):
    member = get_or_404(ElderlyMember, member_id)
    db.session.delete(member)
    db.session.commit()
    return "", 204
