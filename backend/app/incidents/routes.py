from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import ElderlyMember, Incident, utcnow
from ..utils import get_or_404, validation_error_response
from .schemas import IncidentSchema

bp = Blueprint("incidents", __name__, url_prefix="/api/incidents")

schema = IncidentSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


@bp.post("")
@roles_required("admin", "staff")
def create_incident():
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    invalid = _member_or_400(data["elderly_member_id"])
    if invalid:
        return invalid

    data.setdefault("occurred_at", utcnow())
    data.setdefault("emergency_contact_notified", False)
    data.setdefault("follow_up_required", False)
    data.setdefault("status", "Open")
    incident = Incident(**data, reported_by_id=int(get_jwt_identity()))
    db.session.add(incident)
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

    for field, value in data.items():
        setattr(incident, field, value)
    db.session.commit()
    return jsonify(incident=incident.to_dict()), 200

# No DELETE endpoint: incident reports are treated as permanent
# safeguarding records, corrected by editing status/resolution_notes,
# never removed.
