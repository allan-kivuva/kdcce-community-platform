from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Activity, ActivityParticipant, ElderlyMember, User, VolunteerProfile
from ..utils import get_or_404, validation_error_response
from .schemas import ActivityParticipantSchema, ActivityParticipantUpdateSchema, ActivitySchema

bp = Blueprint("activities", __name__, url_prefix="/api/activities")

activity_schema = ActivitySchema()
participant_schema = ActivityParticipantSchema()
participant_update_schema = ActivityParticipantUpdateSchema()


def _facilitator_or_400(user_id):
    """Same rule as HomeVisit.assigned_to_id: staff/admin, or a volunteer
    only once their profile is Verified — never an unverified one."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(error="Validation failed", details={"facilitator_id": ["User not found"]}), 400
    if user.role in ("admin", "staff"):
        return None
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    if profile is None or profile.status != "Verified":
        return jsonify(error="Validation failed", details={"facilitator_id": ["Can only be staff or a verified volunteer"]}), 400
    return None


def _participant_count(activity_id):
    return ActivityParticipant.query.filter_by(activity_id=activity_id).count()


@bp.post("")
@roles_required("admin", "staff")
def create_activity():
    payload = request.get_json(silent=True) or {}
    try:
        data = activity_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    if data.get("facilitator_id") is not None:
        invalid = _facilitator_or_400(data["facilitator_id"])
        if invalid:
            return invalid

    data.setdefault("status", "Scheduled")
    activity = Activity(**data, created_by_id=int(get_jwt_identity()))
    db.session.add(activity)
    db.session.commit()
    return jsonify(activity=activity.to_dict(participant_count=0)), 201


@bp.get("")
@roles_required("admin", "staff")
def list_activities():
    query = Activity.query
    date_str = request.args.get("date")
    if date_str:
        try:
            filter_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify(error="Validation failed", details={"date": ["Must be YYYY-MM-DD"]}), 400
        query = query.filter(db.func.date(Activity.scheduled_at) == filter_date.isoformat())
    activity_type = request.args.get("activity_type")
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type)
    status = request.args.get("status")
    if status:
        query = query.filter(Activity.status == status)

    activities = query.order_by(Activity.scheduled_at.desc()).all()
    return jsonify(activities=[a.to_dict(participant_count=_participant_count(a.id)) for a in activities]), 200


@bp.get("/<int:activity_id>")
@roles_required("admin", "staff")
def get_activity(activity_id):
    activity = get_or_404(Activity, activity_id)
    return jsonify(activity=activity.to_dict(participant_count=_participant_count(activity.id))), 200


@bp.patch("/<int:activity_id>")
@roles_required("admin", "staff")
def update_activity(activity_id):
    activity = get_or_404(Activity, activity_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = activity_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "facilitator_id" in data and data["facilitator_id"] is not None:
        invalid = _facilitator_or_400(data["facilitator_id"])
        if invalid:
            return invalid

    for field, value in data.items():
        setattr(activity, field, value)
    db.session.commit()
    return jsonify(activity=activity.to_dict(participant_count=_participant_count(activity.id))), 200


@bp.delete("/<int:activity_id>")
@roles_required("admin")
def delete_activity(activity_id):
    activity = get_or_404(Activity, activity_id)
    db.session.delete(activity)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="This activity has registered participants and cannot be deleted."), 409
    return "", 204


# ---------- Participants ----------

@bp.post("/<int:activity_id>/participants")
@roles_required("admin", "staff")
def register_participant(activity_id):
    get_or_404(Activity, activity_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = participant_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    if db.session.get(ElderlyMember, data["elderly_member_id"]) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400

    existing = ActivityParticipant.query.filter_by(activity_id=activity_id, elderly_member_id=data["elderly_member_id"]).first()
    if existing is not None:
        return jsonify(error="This member is already registered for this activity"), 409

    participant = ActivityParticipant(activity_id=activity_id, elderly_member_id=data["elderly_member_id"], notes=data.get("notes"), recorded_by_id=int(get_jwt_identity()))
    db.session.add(participant)
    db.session.commit()
    return jsonify(participant=participant.to_dict()), 201


@bp.get("/<int:activity_id>/participants")
@roles_required("admin", "staff")
def list_participants(activity_id):
    get_or_404(Activity, activity_id)
    participants = ActivityParticipant.query.filter_by(activity_id=activity_id).order_by(ActivityParticipant.created_at.asc()).all()
    return jsonify(participants=[p.to_dict() for p in participants]), 200


@bp.patch("/<int:activity_id>/participants/<int:participant_id>")
@roles_required("admin", "staff")
def update_participant(activity_id, participant_id):
    participant = ActivityParticipant.query.filter_by(id=participant_id, activity_id=activity_id).first()
    if participant is None:
        return jsonify(error="ActivityParticipant not found"), 404

    payload = request.get_json(silent=True) or {}
    try:
        data = participant_update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    for field, value in data.items():
        setattr(participant, field, value)
    db.session.commit()
    return jsonify(participant=participant.to_dict()), 200
