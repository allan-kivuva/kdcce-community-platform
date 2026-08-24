from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import ElderlyMember, HomeVisit, User, VolunteerProfile, utcnow
from ..notifications.service import notify
from ..utils import get_or_404, validation_error_response
from .schemas import HomeVisitAssigneeUpdateSchema, HomeVisitCreateSchema, HomeVisitStaffUpdateSchema

bp = Blueprint("homevisits", __name__, url_prefix="/api/home-visits")

create_schema = HomeVisitCreateSchema()
staff_update_schema = HomeVisitStaffUpdateSchema()
assignee_update_schema = HomeVisitAssigneeUpdateSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


def _is_verified_volunteer(user_id):
    """A volunteer's access here must track their CURRENT status, not just
    whatever assigned_to_id was set to at assignment time — if a verified
    volunteer with active visits is later rejected, they must lose access
    to those visits immediately, even though assigned_to_id still points
    at them. Relying only on "assigned_to_id == me" would miss that case,
    since a rejection doesn't retroactively clear existing assignments."""
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    return profile is not None and profile.status == "Verified"


def _assignee_or_400(user_id):
    """A visit may be assigned to staff/admin (a caregiver) or a volunteer
    whose profile has been verified — never an unverified volunteer."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(error="Validation failed", details={"assigned_to_id": ["User not found"]}), 400
    if user.role in ("admin", "staff"):
        return None
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    if profile is None or profile.status != "Verified":
        return jsonify(error="Validation failed", details={"assigned_to_id": ["Can only assign staff or a verified volunteer"]}), 400
    return None


@bp.get("/assignees")
@roles_required("admin", "staff")
def list_assignees():
    """Who this visit could be assigned to: every staff/admin, plus any
    volunteer whose profile is Verified. Purpose-built for the assignment
    dropdown — there's no general user-listing endpoint in this app."""
    staff = User.query.filter(User.role.in_(("admin", "staff"))).order_by(User.name.asc()).all()
    verified = (
        db.session.query(User)
        .join(VolunteerProfile, VolunteerProfile.user_id == User.id)
        .filter(VolunteerProfile.status == "Verified")
        .order_by(User.name.asc())
        .all()
    )
    people = [{"id": u.id, "name": u.name, "role": u.role} for u in staff]
    people += [{"id": u.id, "name": u.name, "role": "volunteer"} for u in verified]
    return jsonify(assignees=people), 200


@bp.post("")
@roles_required("admin", "staff")
def create_visit():
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

    data.setdefault("priority", "Medium")
    status = "Assigned" if data.get("assigned_to_id") else "Pending"
    visit = HomeVisit(**data, status=status, requested_by_id=int(get_jwt_identity()))
    db.session.add(visit)
    db.session.flush()  # assigns visit.id so the notification can reference it
    if visit.assigned_to_id:
        notify(
            visit.assigned_to_id, "Home Visit Assignment", "Home visit assigned to you",
            f"You have been assigned a home visit for {visit.elderly_member.full_name}.",
            related_resource_type="home_visit", related_resource_id=visit.id,
        )
    db.session.commit()
    return jsonify(visit=visit.to_dict()), 201


@bp.get("")
@jwt_required()
def list_visits():
    role = get_jwt().get("role")
    query = HomeVisit.query

    if role == "volunteer":
        if not _is_verified_volunteer(int(get_jwt_identity())):
            return jsonify(error="Forbidden"), 403
        query = query.filter(HomeVisit.assigned_to_id == int(get_jwt_identity()))
    elif role not in ("admin", "staff"):
        return jsonify(error="Forbidden"), 403
    else:
        assigned_to_id = request.args.get("assigned_to_id", type=int)
        if assigned_to_id:
            query = query.filter(HomeVisit.assigned_to_id == assigned_to_id)
        elderly_member_id = request.args.get("elderly_member_id", type=int)
        if elderly_member_id:
            query = query.filter(HomeVisit.elderly_member_id == elderly_member_id)

    status = request.args.get("status")
    if status:
        query = query.filter(HomeVisit.status == status)
    priority = request.args.get("priority")
    if priority:
        query = query.filter(HomeVisit.priority == priority)

    visits = query.order_by(HomeVisit.created_at.desc()).all()
    return jsonify(visits=[v.to_dict() for v in visits]), 200


@bp.get("/<int:visit_id>")
@jwt_required()
def get_visit(visit_id):
    visit = get_or_404(HomeVisit, visit_id)
    role = get_jwt().get("role")
    if role not in ("admin", "staff"):
        identity = int(get_jwt_identity())
        if visit.assigned_to_id != identity or not _is_verified_volunteer(identity):
            return jsonify(error="Forbidden"), 403
    return jsonify(visit=visit.to_dict()), 200


@bp.patch("/<int:visit_id>")
@jwt_required()
def update_visit(visit_id):
    visit = get_or_404(HomeVisit, visit_id)
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
    elif visit.assigned_to_id == int(get_jwt_identity()) and _is_verified_volunteer(int(get_jwt_identity())):
        try:
            data = assignee_update_schema.load(payload, partial=True)
        except ValidationError as err:
            return validation_error_response(err)
    else:
        return jsonify(error="Forbidden"), 403

    if data.get("status") == "Completed" and visit.completed_at is None:
        data["completed_at"] = utcnow()

    previous_assignee = visit.assigned_to_id
    for field, value in data.items():
        setattr(visit, field, value)

    if visit.assigned_to_id and visit.assigned_to_id != previous_assignee:
        notify(
            visit.assigned_to_id, "Home Visit Assignment", "Home visit assigned to you",
            f"You have been assigned a home visit for {visit.elderly_member.full_name}.",
            related_resource_type="home_visit", related_resource_id=visit.id,
        )

    db.session.commit()
    return jsonify(visit=visit.to_dict()), 200


@bp.delete("/<int:visit_id>")
@roles_required("admin")
def delete_visit(visit_id):
    visit = get_or_404(HomeVisit, visit_id)
    db.session.delete(visit)
    db.session.commit()
    return "", 204
