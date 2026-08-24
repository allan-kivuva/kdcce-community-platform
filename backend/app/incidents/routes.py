from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..followups.service import create_from_source
from ..models import ElderlyMember, Incident, User, VolunteerProfile, utcnow
from ..notifications.service import notify
from ..utils import get_or_404, validation_error_response
from .schemas import IncidentSchema, IncidentVolunteerCreateSchema

bp = Blueprint("incidents", __name__, url_prefix="/api/incidents")

schema = IncidentSchema()
volunteer_create_schema = IncidentVolunteerCreateSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


def _is_verified_volunteer(user_id):
    """Same reasoning as the identical helper in homevisits/assistance —
    a volunteer's ability to report a concern tracks their CURRENT
    verification status."""
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    return profile is not None and profile.status == "Verified"


def _notify_critical(incident):
    """Critical incidents notify every admin/staff, same broadcast
    pattern already used for low-stock alerts — reuses notify(), not a
    second notification path."""
    subject = incident.elderly_member.full_name if incident.elderly_member else "General concern (no specific member)"
    for user in User.query.filter(User.role.in_(("admin", "staff"))).all():
        notify(
            user.id, "Critical Incident", f"Critical incident: {incident.incident_type}",
            f"{subject} — {incident.description[:200]}",
            related_resource_type="incident", related_resource_id=incident.id,
        )


@bp.post("")
@jwt_required()
def create_incident():
    """Admin/staff get the full IncidentSchema (status, resolution,
    emergency-contact fields, a client-supplied occurred_at). A verified
    volunteer instead hits IncidentVolunteerCreateSchema — this is the
    "Report a Concern" action: a much smaller field set, occurred_at/
    status/emergency-contact fields always server-set, never client input.
    Either way the row this creates is a real Incident, and Critical
    severity still fires the same _notify_critical() broadcast — one
    incident table, one notification path, regardless of who reported it."""
    role = get_jwt().get("role")
    payload = request.get_json(silent=True) or {}

    if role in ("admin", "staff"):
        try:
            data = schema.load(payload)
        except ValidationError as err:
            return validation_error_response(err)
        data.setdefault("occurred_at", utcnow())
        data.setdefault("emergency_contact_notified", False)
        data.setdefault("status", "Open")
    elif role == "volunteer" and _is_verified_volunteer(int(get_jwt_identity())):
        try:
            data = volunteer_create_schema.load(payload)
        except ValidationError as err:
            return validation_error_response(err)
        data["occurred_at"] = utcnow()
        data["emergency_contact_notified"] = False
        data["status"] = "Open"
    else:
        return jsonify(error="Forbidden"), 403

    data.setdefault("follow_up_required", False)
    data.setdefault("severity", "Medium")

    if data.get("elderly_member_id") is not None:
        invalid = _member_or_400(data["elderly_member_id"])
        if invalid:
            return invalid

    incident = Incident(**data, reported_by_id=int(get_jwt_identity()))
    db.session.add(incident)
    db.session.flush()  # assigns incident.id so notifications/follow-ups can reference it

    if incident.severity == "Critical":
        _notify_critical(incident)
    if incident.follow_up_required and incident.elderly_member_id is not None:
        # FollowUp.elderly_member_id is a real, non-nullable FK — a concern
        # report with no named member has nothing for a follow-up to attach
        # to, so there's simply no follow-up task to create in that case.
        create_from_source(
            incident.elderly_member_id, "incident", incident.id,
            incident.follow_up_notes or f"Follow-up required after a {incident.incident_type} incident.",
            int(get_jwt_identity()),
        )

    db.session.commit()
    return jsonify(incident=incident.to_dict()), 201


@bp.get("")
@roles_required("admin", "staff")
def list_incidents():
    query = Incident.query
    elderly_member_id = request.args.get("elderly_member_id", type=int)
    if elderly_member_id:
        query = query.filter(Incident.elderly_member_id == elderly_member_id)
    incident_type = request.args.get("incident_type")
    if incident_type:
        query = query.filter(Incident.incident_type == incident_type)
    severity = request.args.get("severity")
    if severity:
        query = query.filter(Incident.severity == severity)
    status = request.args.get("status")
    if status:
        query = query.filter(Incident.status == status)
    follow_up_required = request.args.get("follow_up_required")
    if follow_up_required is not None:
        query = query.filter(Incident.follow_up_required == (follow_up_required.lower() == "true"))

    incidents = query.order_by(Incident.occurred_at.desc()).all()
    return jsonify(incidents=[i.to_dict() for i in incidents]), 200


@bp.get("/<int:incident_id>")
@roles_required("admin", "staff")
def get_incident(incident_id):
    incident = get_or_404(Incident, incident_id)
    return jsonify(incident=incident.to_dict()), 200


@bp.patch("/<int:incident_id>")
@roles_required("admin", "staff")
def update_incident(incident_id):
    incident = get_or_404(Incident, incident_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "elderly_member_id" in data:
        invalid = _member_or_400(data["elderly_member_id"])
        if invalid:
            return invalid

    was_critical = incident.severity == "Critical"
    was_follow_up_required = incident.follow_up_required
    for field, value in data.items():
        setattr(incident, field, value)

    if incident.severity == "Critical" and not was_critical:
        _notify_critical(incident)
    if incident.follow_up_required and not was_follow_up_required and incident.elderly_member_id is not None:
        create_from_source(
            incident.elderly_member_id, "incident", incident.id,
            incident.follow_up_notes or f"Follow-up required after a {incident.incident_type} incident.",
            int(get_jwt_identity()),
        )

    db.session.commit()
    return jsonify(incident=incident.to_dict()), 200

# No DELETE endpoint: incident reports are treated as permanent
# safeguarding records, corrected by editing status/resolution_notes,
# never removed.
