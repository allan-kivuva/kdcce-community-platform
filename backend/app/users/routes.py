from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import LoginHistory, User, VolunteerProfile, utcnow
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import RoleChangeSchema, StatusChangeSchema, UserCreateSchema, UserUpdateSchema

# The whole /api/users surface is admin-only. Phase 7 keeps this simple
# and default-deny rather than carving out a partial staff allowance —
# see the Phase 7 report for why ("keep roles simple" / no DB-backed
# permission table). Staff's own account/session self-service already
# works through /api/auth/me and /api/sessions, which don't live here.
bp = Blueprint("users", __name__, url_prefix="/api/users")

create_schema = UserCreateSchema()
update_schema = UserUpdateSchema()
role_schema = RoleChangeSchema()
status_schema = StatusChangeSchema()


def _volunteer_statuses(users):
    ids = [u.id for u in users if u.role == "volunteer"]
    if not ids:
        return {}
    rows = VolunteerProfile.query.filter(VolunteerProfile.user_id.in_(ids)).all()
    return {row.user_id: row.status for row in rows}


@bp.get("/me/login-history")
@jwt_required()
def my_login_history():
    """Self-service — any authenticated user can see their own recent
    logins, no role restriction beyond being logged in as that user."""
    identity = int(get_jwt_identity())
    items = (
        LoginHistory.query.filter_by(user_id=identity)
        .order_by(LoginHistory.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify(login_history=[i.to_dict() for i in items]), 200


@bp.get("")
@roles_required("admin")
def list_users():
    query = User.query

    role = request.args.get("role")
    if role:
        query = query.filter_by(role=role)

    active_param = request.args.get("active")
    if active_param is not None:
        query = query.filter_by(active=active_param.lower() == "true")

    include_deleted = request.args.get("include_deleted", "false").lower() == "true"
    if not include_deleted:
        query = query.filter(User.deleted_at.is_(None))

    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    query = query.order_by(User.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    statuses = _volunteer_statuses(items)
    return jsonify(
        users=[service.user_summary(u, statuses.get(u.id)) for u in items],
        pagination={"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page if per_page else 0},
    ), 200


@bp.post("")
@roles_required("admin")
def create_user():
    """Direct admin/staff/volunteer account creation — the only way to
    create an elevated (admin/staff) account over the network; public
    self-signup (POST /api/auth/register) always creates a volunteer."""
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    email = data["email"].lower()
    if User.query.filter_by(email=email).first():
        return jsonify(error="A user with that email already exists"), 409

    user = User(name=data["name"].strip(), email=email, role=data["role"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()  # assigns user.id without committing yet

    volunteer_status = None
    if data["role"] == "volunteer":
        # Preserve the same invariant self-signup guarantees: every
        # volunteer-role User has exactly one VolunteerProfile, starting
        # Pending just like a self-registered one.
        volunteer_status = "Pending"
        db.session.add(VolunteerProfile(user_id=user.id, status=volunteer_status))

    log_action(int(get_jwt_identity()), "create", "user", user.id, after={"role": user.role, "email": user.email})
    db.session.commit()
    return jsonify(user=service.user_summary(user, volunteer_status)), 201


@bp.get("/<int:user_id>")
@roles_required("admin")
def get_user(user_id):
    user = get_or_404(User, user_id)
    profile = VolunteerProfile.query.filter_by(user_id=user.id).first() if user.role == "volunteer" else None
    return jsonify(user=service.user_summary(user, profile.status if profile else None)), 200


@bp.patch("/<int:user_id>")
@roles_required("admin")
def update_user(user_id):
    user = get_or_404(User, user_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "email" in data:
        email = data["email"].lower()
        existing = User.query.filter_by(email=email).first()
        if existing is not None and existing.id != user.id:
            return jsonify(error="A user with that email already exists"), 409
        data["email"] = email

    before = {"name": user.name, "email": user.email}
    for field, value in data.items():
        setattr(user, field, value)
    after = {"name": user.name, "email": user.email}
    if before != after:
        log_action(int(get_jwt_identity()), "update", "user", user.id, before=before, after=after)

    db.session.commit()
    return jsonify(user=service.user_summary(user)), 200


@bp.patch("/<int:user_id>/role")
@roles_required("admin")
def change_role(user_id):
    user = get_or_404(User, user_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = role_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    new_role = data["role"]
    if new_role == user.role:
        return jsonify(user=service.user_summary(user)), 200

    if service.would_remove_last_admin(user, becoming_role=new_role):
        return jsonify(error="This is the last active admin account — promote another admin first"), 409

    before_role = user.role
    user.role = new_role
    if new_role == "volunteer" and VolunteerProfile.query.filter_by(user_id=user.id).first() is None:
        db.session.add(VolunteerProfile(user_id=user.id))

    log_action(int(get_jwt_identity()), "role_change", "user", user.id, before={"role": before_role}, after={"role": new_role})
    db.session.commit()
    return jsonify(user=service.user_summary(user)), 200


@bp.patch("/<int:user_id>/status")
@roles_required("admin")
def change_status(user_id):
    user = get_or_404(User, user_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = status_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    new_active = data["active"]
    if new_active == user.active:
        return jsonify(user=service.user_summary(user)), 200

    if service.would_remove_last_admin(user, becoming_active=new_active):
        return jsonify(error="This is the last active admin account — it cannot be deactivated"), 409

    before_active = user.active
    user.active = new_active
    log_action(
        int(get_jwt_identity()), "activate" if new_active else "deactivate", "user", user.id,
        before={"active": before_active}, after={"active": new_active},
    )
    db.session.commit()
    return jsonify(user=service.user_summary(user)), 200


@bp.post("/<int:user_id>/reset-password")
@roles_required("admin")
def reset_password(user_id):
    """There is no email-delivery infrastructure in this codebase (see
    Phase 7 report) — so this is an admin-issued temporary password, not
    a self-service emailed reset link. The plaintext is returned exactly
    once, to the admin who requested it, for them to relay out of band;
    it is never logged or stored anywhere but the (hashed) password
    column itself."""
    user = get_or_404(User, user_id)
    temporary_password = service.generate_temporary_password()
    user.set_password(temporary_password)

    log_action(int(get_jwt_identity()), "reset_password", "user", user.id)
    db.session.commit()
    return jsonify(temporary_password=temporary_password), 200


@bp.delete("/<int:user_id>")
@roles_required("admin")
def delete_user(user_id):
    """Soft delete — see Phase 7 report for why users specifically get
    this (and why it wasn't extended to every table)."""
    user = get_or_404(User, user_id)
    if user.deleted_at is not None:
        return "", 204

    if service.would_remove_last_admin(user, becoming_active=False):
        return jsonify(error="This is the last active admin account — it cannot be deleted"), 409

    user.deleted_at = utcnow()
    user.active = False
    log_action(int(get_jwt_identity()), "delete", "user", user.id)
    db.session.commit()
    return "", 204


@bp.post("/<int:user_id>/restore")
@roles_required("admin")
def restore_user(user_id):
    user = get_or_404(User, user_id)
    if user.deleted_at is None:
        return jsonify(user=service.user_summary(user)), 200

    user.deleted_at = None
    user.active = True
    log_action(int(get_jwt_identity()), "restore", "user", user.id)
    db.session.commit()
    return jsonify(user=service.user_summary(user)), 200
