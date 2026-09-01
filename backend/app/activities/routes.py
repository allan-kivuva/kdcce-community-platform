from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Activity, ActivityParticipant, ActivityVolunteer, ElderlyMember, Program, User, VolunteerProfile, utcnow
from ..notifications.service import notify
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import (
    ActivityParticipantSchema, ActivityParticipantUpdateSchema, ActivitySchema,
    ActivityVolunteerAssignSchema, ActivityVolunteerSelfResponseSchema, ActivityVolunteerUpdateSchema,
)

bp = Blueprint("activities", __name__, url_prefix="/api/activities")

activity_schema = ActivitySchema()
participant_schema = ActivityParticipantSchema()
participant_update_schema = ActivityParticipantUpdateSchema()
volunteer_assign_schema = ActivityVolunteerAssignSchema()
volunteer_update_schema = ActivityVolunteerUpdateSchema()
volunteer_self_response_schema = ActivityVolunteerSelfResponseSchema()


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


def _program_or_400(program_id):
    if db.session.get(Program, program_id) is None:
        return jsonify(error="Validation failed", details={"program_id": ["Program not found"]}), 400
    return None


def _participant_count(activity_id):
    return ActivityParticipant.query.filter_by(activity_id=activity_id).count()


def _activity_dict(activity):
    return activity.to_dict(
        participant_count=_participant_count(activity.id),
        confirmed_volunteer_count=service.confirmed_volunteer_count(activity.id),
        waitlist_count=service.waitlist_count(activity.id),
    )


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
    if data.get("program_id") is not None:
        invalid = _program_or_400(data["program_id"])
        if invalid:
            return invalid

    data.setdefault("status", "Scheduled")
    activity = Activity(**data, created_by_id=int(get_jwt_identity()))
    db.session.add(activity)
    db.session.commit()
    return jsonify(activity=_activity_dict(activity)), 201


@bp.get("")
@jwt_required()
def list_activities():
    """Open to any authenticated role — a volunteer needs to browse
    upcoming events to RSVP/see their assignments (the architecture
    audit's gap this phase fills). Nothing sensitive leaks: no elderly
    participant identities here, just title/schedule/location/capacity —
    the elderly roster stays behind list_participants, admin/staff only,
    unchanged."""
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
    program_id = request.args.get("program_id", type=int)
    if program_id is not None:
        query = query.filter(Activity.program_id == program_id)

    activities = query.order_by(Activity.scheduled_at.desc()).all()
    return jsonify(activities=[_activity_dict(a) for a in activities]), 200


@bp.get("/<int:activity_id>")
@jwt_required()
def get_activity(activity_id):
    activity = get_or_404(Activity, activity_id)
    return jsonify(activity=_activity_dict(activity)), 200


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
    if "program_id" in data and data["program_id"] is not None:
        invalid = _program_or_400(data["program_id"])
        if invalid:
            return invalid

    for field, value in data.items():
        setattr(activity, field, value)
    db.session.commit()
    return jsonify(activity=_activity_dict(activity)), 200


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


# ---------- Participants (elderly members — staff-managed, unchanged) ----------

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


# ---------- Volunteer RSVP (self-service) ----------

@bp.post("/<int:activity_id>/rsvp")
@roles_required("volunteer")
def rsvp(activity_id):
    activity = get_or_404(Activity, activity_id)
    identity = int(get_jwt_identity())
    try:
        row = service.self_rsvp(activity, identity)
    except service.RsvpError as err:
        return jsonify(error=err.message), 409

    if row.status == "Waitlisted":
        notify(identity, "Event Waitlisted", f'You are on the waitlist for "{activity.title}"',
               "This event is at capacity — you'll be notified automatically if a spot opens up.",
               related_resource_type="activity", related_resource_id=activity.id)
    else:
        notify(identity, "Event RSVP Confirmed", f'RSVP confirmed for "{activity.title}"',
               f"You're confirmed for {activity.title} on {activity.scheduled_at.strftime('%B %d, %Y')}.",
               related_resource_type="activity", related_resource_id=activity.id)
    db.session.commit()
    return jsonify(assignment=row.to_dict()), 201


@bp.delete("/<int:activity_id>/rsvp")
@roles_required("volunteer")
def cancel_rsvp(activity_id):
    activity = get_or_404(Activity, activity_id)
    identity = int(get_jwt_identity())
    try:
        row, promoted = service.cancel_rsvp(activity_id, identity)
    except service.RsvpError as err:
        return jsonify(error=err.message), 409

    if promoted is not None:
        notify(promoted.volunteer_id, "Event Waitlist Promoted", f'A spot opened up for "{activity.title}"',
               "You've been moved from the waitlist to confirmed — we look forward to seeing you there.",
               related_resource_type="activity", related_resource_id=activity_id)
    db.session.commit()
    return jsonify(assignment=row.to_dict()), 200


@bp.get("/me/assignments")
@roles_required("volunteer")
def my_assignments():
    """Every ActivityVolunteer row belonging to the caller — both their
    own self-RSVPs (assigned_by_id is null) and staffing shifts staff
    assigned them to. The frontend splits "My RSVPs" vs "My Assignments"
    on that same is_self_rsvp flag rather than this needing two
    endpoints."""
    identity = int(get_jwt_identity())
    rows = ActivityVolunteer.query.filter_by(volunteer_id=identity).order_by(ActivityVolunteer.assigned_at.desc()).all()
    result = []
    for row in rows:
        entry = row.to_dict()
        entry["activity"] = row.activity.to_dict()
        result.append(entry)
    return jsonify(assignments=result), 200


# ---------- Volunteer staffing (admin/staff-managed assignment) ----------

@bp.get("/<int:activity_id>/volunteers")
@roles_required("admin", "staff")
def list_activity_volunteers(activity_id):
    get_or_404(Activity, activity_id)
    rows = ActivityVolunteer.query.filter_by(activity_id=activity_id).order_by(ActivityVolunteer.assigned_at.asc()).all()
    return jsonify(volunteers=[r.to_dict() for r in rows]), 200


@bp.get("/<int:activity_id>/waitlist")
@roles_required("admin", "staff")
def list_activity_waitlist(activity_id):
    get_or_404(Activity, activity_id)
    rows = (
        ActivityVolunteer.query.filter_by(activity_id=activity_id, status="Waitlisted")
        .order_by(ActivityVolunteer.assigned_at.asc())
        .all()
    )
    return jsonify(waitlist=[r.to_dict() for r in rows]), 200


@bp.post("/<int:activity_id>/volunteers")
@roles_required("admin", "staff")
def assign_volunteer(activity_id):
    activity = get_or_404(Activity, activity_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = volunteer_assign_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    target = db.session.get(User, data["volunteer_id"])
    if target is None or target.role != "volunteer":
        return jsonify(error="Validation failed", details={"volunteer_id": ["Must be an existing volunteer"]}), 400

    try:
        row = service.staff_assign(activity, data["volunteer_id"], data["role"], int(get_jwt_identity()))
    except service.RsvpError as err:
        return jsonify(error=err.message), 409

    notify(data["volunteer_id"], "Event Assigned", f'You\'ve been assigned to "{activity.title}"',
           f"Role: {data['role']}. {activity.scheduled_at.strftime('%B %d, %Y')}"
           + (f" at {activity.location}" if activity.location else "") + ".",
           related_resource_type="activity", related_resource_id=activity.id)
    db.session.commit()
    return jsonify(assignment=row.to_dict()), 201


def _assignment_or_404(activity_id, assignment_id):
    return ActivityVolunteer.query.filter_by(id=assignment_id, activity_id=activity_id).first()


@bp.patch("/<int:activity_id>/volunteers/<int:assignment_id>")
@jwt_required()
def update_activity_volunteer(activity_id, assignment_id):
    row = _assignment_or_404(activity_id, assignment_id)
    if row is None:
        return jsonify(error="Assignment not found"), 404

    role = get_jwt().get("role")
    identity = int(get_jwt_identity())

    if role in ("admin", "staff"):
        payload = request.get_json(silent=True) or {}
        try:
            data = volunteer_update_schema.load(payload, partial=True)
        except ValidationError as err:
            return validation_error_response(err)
        if "role" in data:
            row.role = data["role"]
        if "status" in data:
            row.status = data["status"]
            if data["status"] == "Confirmed" and row.confirmed_at is None:
                row.confirmed_at = utcnow()
        if data.get("checked_in"):
            row.checked_in_at = row.checked_in_at or utcnow()
        if data.get("checked_out"):
            row.checked_out_at = row.checked_out_at or utcnow()
        db.session.commit()
        return jsonify(assignment=row.to_dict()), 200

    # A volunteer may only respond to their own assignment — confirm or
    # decline, nothing else (not role, not attendance, not anyone else's row).
    if row.volunteer_id != identity:
        return jsonify(error="Forbidden"), 403
    payload = request.get_json(silent=True) or {}
    try:
        data = volunteer_self_response_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)
    row.status = data["status"]
    if data["status"] == "Confirmed":
        row.confirmed_at = utcnow()
    db.session.commit()
    return jsonify(assignment=row.to_dict()), 200
