from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity


def roles_required(*allowed_roles):
    """Restrict a route to the given roles. Always checks the JWT's role
    claim server-side — never trusts anything the client sends.

    Phase 7 hardening: also re-checks the user is still active and not
    soft-deleted on every call, not just at token-mint time. Without
    this, deactivating or deleting an admin/staff account would have no
    effect on any access token they minted before that point until it
    naturally expires (up to 1h) — every route already funneled through
    this one decorator, so this is the single place to close that gap
    for all of them at once, in prep for Phase 8's centralized guards."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            role = get_jwt().get("role")
            if role not in allowed_roles:
                return jsonify(error="Forbidden"), 403

            from ..extensions import db
            from ..models import User

            user = db.session.get(User, int(get_jwt_identity()))
            if user is None or not user.active or user.deleted_at is not None:
                return jsonify(error="Forbidden"), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator
