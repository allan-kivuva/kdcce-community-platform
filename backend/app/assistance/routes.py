from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..assignments.schemas import AssignmentMessageCreateSchema, AssignmentReviewCreateSchema
from ..assignments.service import (
    AttachmentError, attachment_file_path, get_attachment, get_review, list_messages, save_photo, send_message, submit_review,
)
from ..auth.decorators import roles_required
from ..extensions import db
from ..followups.service import create_from_source
from ..models import AssistanceRequest, ElderlyMember, HomeVisit, User, VolunteerProfile, utcnow
from ..notifications.service import notify
from ..utils import get_or_404, validation_error_response
from .schemas import AssistanceRequestAssigneeUpdateSchema, AssistanceRequestCreateSchema, AssistanceRequestStaffUpdateSchema

bp = Blueprint("assistance", __name__, url_prefix="/api/assistance-requests")

create_schema = AssistanceRequestCreateSchema()
staff_update_schema = AssistanceRequestStaffUpdateSchema()
assignee_update_schema = AssistanceRequestAssigneeUpdateSchema()
message_schema = AssignmentMessageCreateSchema()
review_schema = AssignmentReviewCreateSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


def _is_verified_volunteer(user_id):
    """Access must track CURRENT status, not just assigned_to_id — if a
    verified volunteer with active requests is later rejected, they lose
    access to those requests immediately, even though assigned_to_id still
    points at them (a rejection doesn't retroactively clear it). Same
    reasoning as homevisits/routes.py's identical helper."""
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    return profile is not None and profile.status == "Verified"


def _can_access_request(req, role, identity):
    """Same access rule get_request already applies to the request itself
    — photo/message access can never be broader than viewing it."""
    if role in ("admin", "staff"):
        return True
    return req.assigned_to_id == identity and _is_verified_volunteer(identity)


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
    db.session.flush()  # assigns req.id so the notification can reference it
    if req.assigned_to_id:
        notify(
            req.assigned_to_id, "Assistance Request Assignment", "Assistance request assigned to you",
            f"You have been assigned a {req.request_type} request for {req.elderly_member.full_name}.",
            related_resource_type="assistance_request", related_resource_id=req.id,
        )
    db.session.commit()
    return jsonify(request=req.to_dict()), 201


@bp.get("")
@jwt_required()
def list_requests():
    role = get_jwt().get("role")
    query = AssistanceRequest.query

    if role == "volunteer":
        if not _is_verified_volunteer(int(get_jwt_identity())):
            return jsonify(error="Forbidden"), 403
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
    if role not in ("admin", "staff"):
        identity = int(get_jwt_identity())
        if req.assigned_to_id != identity or not _is_verified_volunteer(identity):
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
    elif req.assigned_to_id == int(get_jwt_identity()) and _is_verified_volunteer(int(get_jwt_identity())):
        try:
            data = assignee_update_schema.load(payload, partial=True)
        except ValidationError as err:
            return validation_error_response(err)
    else:
        return jsonify(error="Forbidden"), 403

    if data.get("status") == "Started" and req.started_at is None:
        data["started_at"] = utcnow()
    if data.get("status") == "Completed" and req.completed_at is None:
        data["completed_at"] = utcnow()

    previous_assignee = req.assigned_to_id
    was_follow_up_required = req.follow_up_required
    for field, value in data.items():
        setattr(req, field, value)

    if req.assigned_to_id and req.assigned_to_id != previous_assignee:
        notify(
            req.assigned_to_id, "Assistance Request Assignment", "Assistance request assigned to you",
            f"You have been assigned a {req.request_type} request for {req.elderly_member.full_name}.",
            related_resource_type="assistance_request", related_resource_id=req.id,
        )

    if req.follow_up_required and not was_follow_up_required:
        create_from_source(
            req.elderly_member_id, "assistance_request", req.id,
            req.follow_up_notes or f"Follow-up required after a {req.request_type} request for {req.elderly_member.full_name}.",
            int(get_jwt_identity()), assigned_to_id=req.assigned_to_id,
        )

    db.session.commit()
    return jsonify(request=req.to_dict()), 200


@bp.post("/<int:request_id>/accept")
@jwt_required()
def accept_request(request_id):
    """Acceptance is its own narrow action, not just another PATCH status
    value — only the assigned user can call it, only on their own
    request, only from Assigned."""
    req = get_or_404(AssistanceRequest, request_id)
    identity = int(get_jwt_identity())
    if req.assigned_to_id != identity or not _is_verified_volunteer(identity):
        return jsonify(error="Forbidden"), 403
    if req.status != "Assigned":
        return jsonify(error=f"Cannot accept a request in '{req.status}' status — it must be 'Assigned' first"), 409

    req.status = "Accepted"
    db.session.commit()
    return jsonify(request=req.to_dict()), 200


@bp.post("/<int:request_id>/photo")
@jwt_required()
def upload_request_photo(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    if not _can_access_request(req, role, identity):
        return jsonify(error="Forbidden"), 403

    try:
        attachment = save_photo("assistance_request", req.id, identity, request.files.get("photo"))
    except AttachmentError as err:
        return jsonify(error="Validation failed", details={"photo": [err.message]}), 400

    db.session.commit()
    return jsonify(attachment=attachment.to_dict()), 201


@bp.get("/<int:request_id>/photo")
@jwt_required()
def get_request_photo(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    if not _can_access_request(req, role, identity):
        return jsonify(error="Forbidden"), 403

    attachment = get_attachment("assistance_request", req.id)
    if attachment is None:
        return jsonify(error="No photo for this request"), 404
    return send_file(attachment_file_path(attachment), mimetype=attachment.mime_type, download_name=attachment.original_filename)


@bp.get("/<int:request_id>/messages")
@jwt_required()
def list_request_messages(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    if not _can_access_request(req, role, identity):
        return jsonify(error="Forbidden"), 403
    return jsonify(messages=[m.to_dict() for m in list_messages("assistance_request", req.id)]), 200


@bp.post("/<int:request_id>/messages")
@jwt_required()
def create_request_message(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    if not _can_access_request(req, role, identity):
        return jsonify(error="Forbidden"), 403

    payload = request.get_json(silent=True) or {}
    try:
        data = message_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    message = send_message("assistance_request", req.id, identity, data["body"])
    recipient_id = req.requested_by_id if identity == req.assigned_to_id else req.assigned_to_id
    if recipient_id and recipient_id != identity:
        notify(
            recipient_id, "Assignment Message", "New message on an assistance request",
            f"{message.sender.name}: {data['body'][:200]}",
            related_resource_type="assistance_request", related_resource_id=req.id,
        )
    db.session.commit()
    return jsonify(message=message.to_dict()), 201


@bp.post("/<int:request_id>/review")
@roles_required("admin")
def review_request(request_id):
    """Admin-only, not the usual ("admin", "staff") pair used elsewhere in
    this module — same reasoning as homevisits/routes.py's identical
    endpoint. Only allowed once the request is Completed."""
    req = get_or_404(AssistanceRequest, request_id)
    if req.status != "Completed":
        return jsonify(error="Can only review a request once it is Completed"), 409

    payload = request.get_json(silent=True) or {}
    try:
        data = review_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    review = submit_review("assistance_request", req.id, int(get_jwt_identity()), data["rating"], data.get("comment"))
    if req.assigned_to_id:
        stars = "★" * data["rating"] + "☆" * (5 - data["rating"])
        notify(
            req.assigned_to_id, "Assignment Reviewed", f"Your assistance request was reviewed — {stars}",
            data.get("comment") or f"Rated {data['rating']}/5 stars.",
            related_resource_type="assistance_request", related_resource_id=req.id,
        )
    db.session.commit()
    return jsonify(review=review.to_dict()), 201


@bp.get("/<int:request_id>/review")
@jwt_required()
def get_request_review(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    if not _can_access_request(req, role, identity):
        return jsonify(error="Forbidden"), 403
    review = get_review("assistance_request", req.id)
    if review is None:
        return jsonify(error="No review for this request"), 404
    return jsonify(review=review.to_dict()), 200


@bp.delete("/<int:request_id>")
@roles_required("admin")
def delete_request(request_id):
    req = get_or_404(AssistanceRequest, request_id)
    db.session.delete(req)
    db.session.commit()
    return "", 204
