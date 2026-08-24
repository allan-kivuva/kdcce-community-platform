from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import VolunteerProfile, utcnow
from ..utils import get_or_404, validation_error_response
from .schemas import VolunteerSelfUpdateSchema, VolunteerStaffUpdateSchema

bp = Blueprint("volunteers", __name__, url_prefix="/api/volunteers")

self_schema = VolunteerSelfUpdateSchema()
staff_schema = VolunteerStaffUpdateSchema()


# ---------- Self-service ----------

@bp.get("/me")
@jwt_required()
def get_my_profile():
    profile = VolunteerProfile.query.filter_by(user_id=int(get_jwt_identity())).first()
    if profile is None:
        return jsonify(error="No volunteer profile on this account"), 404
    return jsonify(volunteer=profile.to_dict()), 200


@bp.patch("/me")
@jwt_required()
def update_my_profile():
    profile = VolunteerProfile.query.filter_by(user_id=int(get_jwt_identity())).first()
    if profile is None:
        return jsonify(error="No volunteer profile on this account"), 404

    payload = request.get_json(silent=True) or {}
    try:
        data = self_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    for field, value in data.items():
        setattr(profile, field, value)
    db.session.commit()
    return jsonify(volunteer=profile.to_dict()), 200


# ---------- Staff management ----------

@bp.get("")
@roles_required("admin", "staff")
def list_volunteers():
    query = VolunteerProfile.query
    status = request.args.get("status")
    if status:
        query = query.filter(VolunteerProfile.status == status)
    profiles = query.order_by(VolunteerProfile.created_at.desc()).all()
    return jsonify(volunteers=[p.to_dict() for p in profiles]), 200


@bp.get("/<int:volunteer_id>")
@roles_required("admin", "staff")
def get_volunteer(volunteer_id):
    profile = get_or_404(VolunteerProfile, volunteer_id)
    return jsonify(volunteer=profile.to_dict()), 200


@bp.patch("/<int:volunteer_id>")
@roles_required("admin", "staff")
def update_volunteer(volunteer_id):
    profile = get_or_404(VolunteerProfile, volunteer_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = staff_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "status" in data and data["status"] != profile.status:
        profile.reviewed_by_id = int(get_jwt_identity())
        profile.reviewed_at = utcnow()

    for field, value in data.items():
        setattr(profile, field, value)
    db.session.commit()
    return jsonify(volunteer=profile.to_dict()), 200
