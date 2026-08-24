from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import AssistanceRequest, ElderlyMember, HomeVisit, User, VolunteerProfile, utcnow
from ..utils import get_or_404, validation_error_response
from .schemas import AssistanceRequestAssigneeUpdateSchema, AssistanceRequestCreateSchema, AssistanceRequestStaffUpdateSchema

bp = Blueprint("assistance", __name__, url_prefix="/api/assistance-requests")

create_schema = AssistanceRequestCreateSchema()
staff_update_schema = AssistanceRequestStaffUpdateSchema()
assignee_update_schema = AssistanceRequestAssigneeUpdateSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


def _assignee_or_400(user_id):
    """Same rule as HomeVisit.assigned_to_id: staff/admin, or a volunteer
    only once their profile is Verified — never an unverified one."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(error="Validation failed", details={"assigned_to_id": ["User not found"]}), 400
    if user.role in ("admin", "staff"):
        return None
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    if profile is None or profile.status != "Verified":
        return jsonify(error="Validation failed", details={"assigned_to_id": ["Can only assign staff or a verified volunteer"]}), 400
    return None


def _home_visit_or_400(home_visit_id):
    if db.session.get(HomeVisit, home_visit_id) is None:
        return jsonify(error="Validation failed", details={"home_visit_id": ["Home visit not found"]}), 400
    return None


@bp.post("")
@roles_required("admin", "staff")
def create_request():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    invalid = _member_or_400(data["elderly_member_id"])
    if invalid:
        return invalid
    if data.get("assigned_to_id") is not None:
        invalid = _assignee_or_400(data["assigned_to_id"])
        if invalid:
            return invalid
    if data.get("home_visit_id") is not None:
        invalid = _home_visit_or_400(data["home_visit_id"])
        if invalid:
            return invalid

    data.setdefault("priority", "Medium")
    status = "Assigned" if data.get("assigned_to_id") else "Requested"
    req = AssistanceRequest(**data, status=status, requested_by_id=int(get_jwt_identity()))
    db.session.add(req)
    db.session.commit()
    return jsonify(request=req.to_dict()), 201


@bp.get("")
@jwt_required()
def list_requests():
    role = get_jwt().get("role")
    query = AssistanceRequest.query

    if role == "volunteer":
        query = query.filter(AssistanceRequest.assigned_to_id == int(get_jwt_identity()))
    elif role not in ("admin", "staff"):
        return jsonify(error="Forbidden"), 403
    else:
        assigned_to_id = request.args.get("assigned_to_id", type=int)
        if assigned_to_id:
            query = query.filter(AssistanceRequest.assigned_to_id == assigned_to_id)
        elderly_member_id = request.args.get("elderly_member_id", type=int)
        if elderly_member_id:
            query = query.filter(AssistanceRequest.elderly_member_id == elderly_member_id)

    status = request.args.get("status")
    if status:
        query = query.filter(AssistanceRequest.status == status)
    priority = request.args.get("priority")
    if priority:
        query = query.filter(AssistanceRequest.priority == priority)
    request_type = request.args.get("request_type")
    if request_type:
        query = query.filter(AssistanceRequest.request_type == request_type)

    requests_ = query.order_by(AssistanceRequest.created_at.desc()).all()
    return jsonify(requests=[r.to_dict() for r in requests_]), 200


@bp.get("/<int:request_id>")
@jwt_required()
def get_request(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    role = get_jwt().get("role")
    if role not in ("admin", "staff") and req.assigned_to_id != int(get_jwt_identity()):
        return jsonify(error="Forbidden"), 403
    return jsonify(request=req.to_dict()), 200


@bp.patch("/<int:request_id>")
@jwt_required()
def update_request(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    role = get_jwt().get("role")
    payload = request.get_json(silent=True) or {}

    if role in ("admin", "staff"):
        try:
            data = staff_update_schema.load(payload, partial=True)
        except ValidationError as err:
            return validation_error_response(err)
        if "elderly_member_id" in data:
            invalid = _member_or_400(data["elderly_member_id"])
            if invalid:
                return invalid
        if "assigned_to_id" in data and data["assigned_to_id"] is not None:
            invalid = _assignee_or_400(data["assigned_to_id"])
            if invalid:
                return invalid
        if "home_visit_id" in data and data["home_visit_id"] is not None:
            invalid = _home_visit_or_400(data["home_visit_id"])
            if invalid:
                return invalid
    elif req.assigned_to_id == int(get_jwt_identity()):
        try:
            data = assignee_update_schema.load(payload, partial=True)
        except ValidationError as err:
            return validation_error_response(err)
    else:
        return jsonify(error="Forbidden"), 403

    if data.get("status") == "Completed" and req.completed_at is None:
        data["completed_at"] = utcnow()

    for field, value in data.items():
        setattr(req, field, value)
    db.session.commit()
    return jsonify(request=req.to_dict()), 200


@bp.post("/<int:request_id>/accept")
@jwt_required()
def accept_request(request_id):
    """Acceptance is its own narrow action, not just another PATCH status
    value — only the assigned user can call it, only on their own
    request, only from Assigned."""
    req = get_or_404(AssistanceRequest, request_id)
    if req.assigned_to_id != int(get_jwt_identity()):
        return jsonify(error="Forbidden"), 403
    if req.status != "Assigned":
        return jsonify(error=f"Cannot accept a request in '{req.status}' status — it must be 'Assigned' first"), 409

    req.status = "Accepted"
    db.session.commit()
    return jsonify(request=req.to_dict()), 200


@bp.delete("/<int:request_id>")
@roles_required("admin")
def delete_request(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    db.session.delete(req)
    db.session.commit()
    return "", 204
