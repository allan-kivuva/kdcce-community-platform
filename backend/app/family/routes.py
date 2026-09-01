from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import ActivityParticipant, AssistanceRequest, ElderlyMember, FamilyMemberAccess, HomeVisit, MealAttendance, User, utcnow
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import (
    FamilyAccessCreateSchema, family_activity_summary, family_member_summary, family_visit_summary,
)

bp = Blueprint("family", __name__, url_prefix="/api/family")
admin_bp = Blueprint("admin_family_access", __name__, url_prefix="/api/admin/family-access")

create_access_schema = FamilyAccessCreateSchema()


def _access_or_404(user_id, member_id):
    """Never distinguishes "member 13 doesn't exist" from "member 13
    exists but you're not authorized for it" — both come back as a
    plain 404 with no description, exactly the attack this guards
    against (see the Phase 8 brief's own worked example)."""
    access = service.authorized_access(user_id, member_id)
    if access is None:
        abort(404)
    return access


@bp.get("/members")
@roles_required("family")
def list_members():
    identity = int(get_jwt_identity())
    accesses = service.active_accesses_for_user(identity)
    return jsonify(members=[family_member_summary(a.elderly_member, a.relationship_label) for a in accesses]), 200


@bp.get("/members/<int:member_id>")
@roles_required("family")
def get_member(member_id):
    identity = int(get_jwt_identity())
    access = _access_or_404(identity, member_id)
    return jsonify(member=family_member_summary(access.elderly_member, access.relationship_label)), 200


@bp.get("/members/<int:member_id>/visits")
@roles_required("family")
def get_member_visits(member_id):
    identity = int(get_jwt_identity())
    _access_or_404(identity, member_id)
    visits = (
        HomeVisit.query.filter_by(elderly_member_id=member_id)
        .order_by(HomeVisit.scheduled_at.desc(), HomeVisit.created_at.desc())
        .limit(20)
        .all()
    )
    requests = (
        AssistanceRequest.query.filter_by(elderly_member_id=member_id)
        .order_by(AssistanceRequest.scheduled_at.desc(), AssistanceRequest.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify(
        visits=[family_visit_summary(v) for v in visits],
        assistance_requests=[
            {
                "id": r.id, "status": r.status, "request_type": r.request_type,
                "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "assigned_volunteer_name": r.assigned_to.name if r.assigned_to else None,
            }
            for r in requests
        ],
    ), 200


@bp.get("/members/<int:member_id>/programs")
@roles_required("family")
def get_member_programs(member_id):
    identity = int(get_jwt_identity())
    _access_or_404(identity, member_id)
    participants = (
        ActivityParticipant.query.filter_by(elderly_member_id=member_id)
        .order_by(ActivityParticipant.created_at.desc())
        .limit(30)
        .all()
    )
    return jsonify(activities=[family_activity_summary(p) for p in participants]), 200


@bp.get("/members/<int:member_id>/updates")
@roles_required("family")
def get_member_updates(member_id):
    """A merged, read-only activity feed — completed visits, attended
    meals, and attended activities, each stripped to a bare "this
    happened" fact with no staff notes/observations attached. Sorted
    newest first, capped to a reasonable page size."""
    identity = int(get_jwt_identity())
    _access_or_404(identity, member_id)

    updates = []
    for visit in HomeVisit.query.filter_by(elderly_member_id=member_id, status="Completed").order_by(HomeVisit.completed_at.desc()).limit(10).all():
        if visit.completed_at:
            updates.append({"type": "home_visit", "label": "Home visit completed", "at": visit.completed_at.isoformat()})
    for attendance in (
        MealAttendance.query.join(MealAttendance.meal).filter(MealAttendance.elderly_member_id == member_id)
        .order_by(MealAttendance.created_at.desc()).limit(10).all()
    ):
        updates.append({
            "type": "meal", "label": f"{attendance.meal.meal_type} attended", "at": attendance.created_at.isoformat(),
        })
    for participant in (
        ActivityParticipant.query.filter_by(elderly_member_id=member_id, status="Attended")
        .order_by(ActivityParticipant.updated_at.desc()).limit(10).all()
    ):
        updates.append({
            "type": "activity", "label": f"{participant.activity.title} attended",
            "at": participant.updated_at.isoformat(),
        })

    updates.sort(key=lambda u: u["at"], reverse=True)
    return jsonify(updates=updates[:15]), 200


# ---------- Admin/staff management of family relationships ----------

@admin_bp.get("")
@roles_required("admin", "staff")
def list_family_access():
    query = FamilyMemberAccess.query
    elderly_member_id = request.args.get("elderly_member_id", type=int)
    if elderly_member_id is not None:
        query = query.filter_by(elderly_member_id=elderly_member_id)
    user_id = request.args.get("user_id", type=int)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    status = request.args.get("access_status")
    if status:
        query = query.filter_by(access_status=status)
    rows = query.order_by(FamilyMemberAccess.created_at.desc()).all()
    return jsonify(family_access=[r.to_dict() for r in rows]), 200


@admin_bp.post("")
@roles_required("admin", "staff")
def create_family_access():
    """Creates the relationship as Pending — a second admin action
    (approve) is required before it grants any actual access. The
    linked user must already exist with role='family' (created via the
    existing POST /api/users, same as any other account — see Phase 7);
    this endpoint only records the relationship, never creates a user."""
    payload = request.get_json(silent=True) or {}
    try:
        data = create_access_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    user = get_or_404(User, data["user_id"])
    if user.role != "family":
        return jsonify(error="Validation failed", details={"user_id": ["That account is not a family-role account"]}), 400
    get_or_404(ElderlyMember, data["elderly_member_id"])

    if FamilyMemberAccess.query.filter_by(user_id=data["user_id"], elderly_member_id=data["elderly_member_id"]).first():
        return jsonify(error="A relationship between this account and member already exists"), 409

    access = FamilyMemberAccess(
        user_id=data["user_id"], elderly_member_id=data["elderly_member_id"],
        relationship_label=data["relationship"], access_status="Pending",
    )
    db.session.add(access)
    db.session.flush()
    log_action(
        int(get_jwt_identity()), "create", "family_access", access.id,
        after={"user_id": access.user_id, "elderly_member_id": access.elderly_member_id, "access_status": access.access_status},
    )
    db.session.commit()
    return jsonify(family_access=access.to_dict()), 201


@admin_bp.patch("/<int:access_id>/approve")
@roles_required("admin", "staff")
def approve_family_access(access_id):
    access = get_or_404(FamilyMemberAccess, access_id)
    before = access.access_status
    access.access_status = "Active"
    access.approved_by_id = int(get_jwt_identity())
    access.approved_at = utcnow()
    access.revoked_at = None
    log_action(int(get_jwt_identity()), "approve", "family_access", access.id, before={"access_status": before}, after={"access_status": "Active"})
    db.session.commit()
    return jsonify(family_access=access.to_dict()), 200


@admin_bp.patch("/<int:access_id>/suspend")
@roles_required("admin", "staff")
def suspend_family_access(access_id):
    access = get_or_404(FamilyMemberAccess, access_id)
    before = access.access_status
    access.access_status = "Suspended"
    log_action(int(get_jwt_identity()), "suspend", "family_access", access.id, before={"access_status": before}, after={"access_status": "Suspended"})
    db.session.commit()
    return jsonify(family_access=access.to_dict()), 200


@admin_bp.patch("/<int:access_id>/revoke")
@roles_required("admin", "staff")
def revoke_family_access(access_id):
    """Immediate effect — the very next request from this family account
    against this member is re-checked against the DB (see
    family/service.py:authorized_access), not any cache, so revocation
    takes hold on the next request with no propagation delay."""
    access = get_or_404(FamilyMemberAccess, access_id)
    before = access.access_status
    access.access_status = "Revoked"
    access.revoked_at = utcnow()
    log_action(int(get_jwt_identity()), "revoke", "family_access", access.id, before={"access_status": before}, after={"access_status": "Revoked"})
    db.session.commit()
    return jsonify(family_access=access.to_dict()), 200
