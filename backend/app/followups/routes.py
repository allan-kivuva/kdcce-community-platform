from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import Schema, ValidationError, fields, validate

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import ElderlyMember, FollowUp, User, VolunteerProfile, utcnow
from ..notifications.service import notify
from ..utils import get_or_404, validation_error_response
from .schemas import FollowUpCreateSchema, FollowUpUpdateSchema

bp = Blueprint("followups", __name__, url_prefix="/api/followups")

create_schema = FollowUpCreateSchema()
update_schema = FollowUpUpdateSchema()


class _AssigneeUpdateSchema(Schema):
    """What the assigned staff member or verified volunteer may change on
    their own follow-up — progress, not the assignment itself. Same
    restricted-field pattern as HomeVisit/AssistanceRequest's assignee
    schemas."""

    status = fields.String(allow_none=False, validate=validate.OneOf(("In Progress", "Completed")))
    notes = fields.String(allow_none=True, validate=validate.Length(max=2000))


assignee_update_schema = _AssigneeUpdateSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


def _is_verified_volunteer(user_id):
    """Same reasoning as the identical helper in homevisits/assistance:
    access tracks CURRENT status, not who was assigned at creation time."""
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    return profile is not None and profile.status == "Verified"


def _assignee_or_400(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(error="Validation failed", details={"assigned_to_id": ["User not found"]}), 400
    if user.role in ("admin", "staff"):
        return None
    if not _is_verified_volunteer(user_id):
        return jsonify(error="Validation failed", details={"assigned_to_id": ["Can only assign staff or a verified volunteer"]}), 400
    return None


def _can_access(followup, role, identity):
    if role in ("admin", "staff"):
        return True
    return followup.assigned_to_id == identity and _is_verified_volunteer(identity)


@bp.post("")
@roles_required("admin", "staff")
def create_followup():
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

    followup = FollowUp(
        elderly_member_id=data["elderly_member_id"],
        source_type="manual",
        source_id=0,
        reason=data["reason"],
        priority=data["priority"],
        assigned_to_id=data.get("assigned_to_id"),
        due_date=data.get("due_date"),
        notes=data.get("notes"),
        created_by_id=int(get_jwt_identity()),
    )
    db.session.add(followup)
    db.session.commit()
    return jsonify(followup=followup.to_dict()), 201


@bp.get("")
@jwt_required()
def list_followups():
    role = get_jwt().get("role")
    query = FollowUp.query

    if role == "volunteer":
        if not _is_verified_volunteer(int(get_jwt_identity())):
            return jsonify(error="Forbidden"), 403
        query = query.filter(FollowUp.assigned_to_id == int(get_jwt_identity()))
    elif role not in ("admin", "staff"):
        return jsonify(error="Forbidden"), 403
    else:
        elderly_member_id = request.args.get("elderly_member_id", type=int)
        if elderly_member_id:
            query = query.filter(FollowUp.elderly_member_id == elderly_member_id)
        assigned_to_id = request.args.get("assigned_to_id", type=int)
        if assigned_to_id:
            query = query.filter(FollowUp.assigned_to_id == assigned_to_id)

    status = request.args.get("status")
    if status:
        query = query.filter(FollowUp.status == status)
    priority = request.args.get("priority")
    if priority:
        query = query.filter(FollowUp.priority == priority)
    if request.args.get("overdue") == "true":
        query = query.filter(FollowUp.status != "Completed", FollowUp.due_date.isnot(None), FollowUp.due_date < utcnow().date())

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 200)
    query = query.order_by(FollowUp.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        followups=[f.to_dict() for f in items],
        pagination={"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page if per_page else 0},
    ), 200


@bp.get("/<int:followup_id>")
@jwt_required()
def get_followup(followup_id):
    followup = get_or_404(FollowUp, followup_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    if not _can_access(followup, role, identity):
        return jsonify(error="Forbidden"), 403
    return jsonify(followup=followup.to_dict()), 200


@bp.patch("/<int:followup_id>")
@jwt_required()
def update_followup(followup_id):
    followup = get_or_404(FollowUp, followup_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}

    if role in ("admin", "staff"):
        try:
            data = update_schema.load(payload, partial=True)
        except ValidationError as err:
            return validation_error_response(err)
        if "assigned_to_id" in data and data["assigned_to_id"] is not None:
            invalid = _assignee_or_400(data["assigned_to_id"])
            if invalid:
                return invalid
            if data["assigned_to_id"] != followup.assigned_to_id:
                notify(
                    data["assigned_to_id"], "Follow-up Assigned", "New follow-up assigned to you",
                    followup.reason, related_resource_type="follow_up", related_resource_id=followup.id,
                )
    elif followup.assigned_to_id == identity and _is_verified_volunteer(identity):
        try:
            data = assignee_update_schema.load(payload, partial=True)
        except ValidationError as err:
            return validation_error_response(err)
    else:
        return jsonify(error="Forbidden"), 403

    if data.get("status") == "Completed" and followup.completed_at is None:
        data["completed_at"] = utcnow()

    for field, value in data.items():
        setattr(followup, field, value)

    db.session.commit()
    return jsonify(followup=followup.to_dict()), 200
