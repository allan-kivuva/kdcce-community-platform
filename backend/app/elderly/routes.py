from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import OPA, ElderlyMember
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
