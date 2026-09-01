import secrets

from ..models import User


def other_active_admin_count(exclude_user_id):
    """How many active, non-deleted admins exist besides the given user —
    used to guard every action that could take an account out of the
    admin pool (role change, deactivate, soft delete). If this comes
    back 0, the given user (if currently an active admin) is the last
    one and the action must be refused."""
    return User.query.filter(
        User.role == "admin",
        User.active.is_(True),
        User.deleted_at.is_(None),
        User.id != exclude_user_id,
    ).count()


def would_remove_last_admin(user, becoming_active=None, becoming_role=None):
    """True if applying the given change to `user` would leave zero
    active admins platform-wide. Pass whichever of becoming_active/
    becoming_role is actually changing; leave the other as None to mean
    "unchanged". A user who isn't currently counted as an active admin
    can never be the one tripping this guard."""
    currently_counts = user.role == "admin" and user.active and user.deleted_at is None
    if not currently_counts:
        return False

    will_still_count = True
    if becoming_role is not None:
        will_still_count = will_still_count and becoming_role == "admin"
    if becoming_active is not None:
        will_still_count = will_still_count and becoming_active

    if will_still_count:
        return False
    return other_active_admin_count(user.id) == 0


def generate_temporary_password():
    # 12 random URL-safe characters — well above the 8-char minimum
    # RegisterSchema/set_password already enforce, shown to the
    # requesting admin exactly once.
    return secrets.token_urlsafe(9)


def user_summary(user, volunteer_status=None):
    data = user.to_dict()
    data["deleted_at"] = user.deleted_at.isoformat() if user.deleted_at else None
    data["volunteer_status"] = volunteer_status
    return data
