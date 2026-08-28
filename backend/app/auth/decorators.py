from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def roles_required(*allowed_roles):
    """Restrict a route to the given roles. Always checks the JWT's role
    claim server-side — never trusts anything the client sends."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            role = get_jwt().get("role")
            if role not in allowed_roles:
                return jsonify(error="Forbidden"), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
