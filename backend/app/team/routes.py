from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import TeamMember
from ..utils import get_or_404, validation_error_response
from .schemas import TeamMemberSchema

bp = Blueprint("team", __name__)

schema = TeamMemberSchema()


@bp.get("/api/team")
def list_team():
    members = TeamMember.query.order_by(TeamMember.created_at.asc()).all()
    return jsonify(team=[m.to_dict() for m in members]), 200


@bp.post("/api/admin/team")
@roles_required("admin", "staff")
def create_member():
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    member = TeamMember(**data)
    db.session.add(member)
    db.session.commit()
    return jsonify(member=member.to_dict()), 201


@bp.patch("/api/admin/team/<int:member_id>")
@roles_required("admin", "staff")
def update_member(member_id):
    member = get_or_404(TeamMember, member_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    for field, value in data.items():
        setattr(member, field, value)
    db.session.commit()
    return jsonify(member=member.to_dict()), 200


@bp.delete("/api/admin/team/<int:member_id>")
@roles_required("admin", "staff")
def delete_member(member_id):
    member = get_or_404(TeamMember, member_id)
    db.session.delete(member)
    db.session.commit()
    return "", 204
