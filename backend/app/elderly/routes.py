from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..geocoding.service import geocode_address
from ..models import OPA, ElderlyMember, utcnow
from ..utils import csv_response, get_or_404, validation_error_response
from .schemas import OPASchema, ElderlyMemberSchema
from .service import build_member_timeline_events

bp = Blueprint("elderly", __name__)

opa_schema = OPASchema()
member_schema = ElderlyMemberSchema()

_SNAPSHOT_FIELDS = ("member_id", "full_name", "status", "opa_id", "location", "gender")


def _snapshot(member):
    snapshot = {}
    for field in _SNAPSHOT_FIELDS:
        value = getattr(member, field)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        snapshot[field] = value
    return snapshot


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


@bp.post("/api/elderly/export")
@roles_required("admin", "staff")
def export_members():
    """Bulk export — {"ids": [...]} exports exactly those records; an
    omitted/empty ids list exports every member (same permission as the
    plain list endpoint, since this returns nothing list_members()
    doesn't already return). Coordinates are never included — this is
    the same admin-only member roster the list page already shows, not
    the map's data path."""
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids") or []

    query = ElderlyMember.query
    if ids:
        query = query.filter(ElderlyMember.id.in_(ids))
    members = query.order_by(ElderlyMember.full_name.asc()).all()

    rows = [
        [m.member_id, m.full_name, m.gender, m.date_of_birth.isoformat() if m.date_of_birth else "", m.location or "", m.status]
        for m in members
    ]
    log_action(int(get_jwt_identity()), "export", "elderly_member", len(members), after={"count": len(members)})
    db.session.commit()
    return csv_response("elderly_members_export.csv", ["Member ID", "Full Name", "Gender", "Date of Birth", "Location", "Status"], rows)


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
    events = build_member_timeline_events(member_id)

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
    log_action(int(get_jwt_identity()), "create", "elderly_member", member.id, after=_snapshot(member))
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

    before = _snapshot(member)
    for field, value in data.items():
        setattr(member, field, value)
    after = _snapshot(member)
    if after != before:
        log_action(int(get_jwt_identity()), "update", "elderly_member", member.id, before=before, after=after)
    db.session.commit()
    return jsonify(member=member.to_dict()), 200


@bp.post("/api/elderly/<int:member_id>/geocode")
@roles_required("admin", "staff")
def geocode_member(member_id):
    """Opt-in, admin/staff-triggered only — never run automatically on
    create/update. Skips re-geocoding (returns the cached result) unless
    ?force=true is passed, so editing an unrelated field never silently
    re-spends a real geocoder's rate limit once one is wired up."""
    member = get_or_404(ElderlyMember, member_id)
    force = request.args.get("force", "false").lower() == "true"

    if member.geocoded_at is not None and not force:
        return jsonify(member=member.to_dict(include_coordinates=True), geocoded=False, cached=True), 200

    if not member.location or not member.location.strip():
        return jsonify(error="This member has no location text to geocode"), 400

    result = geocode_address(member.location)
    if result is None:
        return jsonify(error="Could not geocode this address"), 422

    before = {"latitude": member.latitude, "longitude": member.longitude}
    member.latitude = result.latitude
    member.longitude = result.longitude
    member.geocoded_at = utcnow()
    member.geocode_source = result.source
    member.geocode_accuracy = result.accuracy
    after = {"latitude": member.latitude, "longitude": member.longitude}

    log_action(int(get_jwt_identity()), "geocode", "elderly_member", member.id, before=before, after=after)
    db.session.commit()
    return jsonify(member=member.to_dict(include_coordinates=True), geocoded=True, cached=False), 200


@bp.delete("/api/elderly/<int:member_id>")
@roles_required("admin")
def delete_member(member_id):
    member = get_or_404(ElderlyMember, member_id)
    log_action(int(get_jwt_identity()), "delete", "elderly_member", member.id, before=_snapshot(member))
    db.session.delete(member)
    db.session.commit()
    return "", 204
