from flask import Blueprint, jsonify, request

from ..auth.decorators import roles_required
from ..models import LoginHistory

bp = Blueprint("login_history", __name__, url_prefix="/api/login-history")


@bp.get("")
@roles_required("admin")
def list_login_history():
    """Admin-only security history — every login attempt, success or
    failure, across every account. A user's OWN recent logins are
    available separately at GET /api/users/me/login-history (no role
    restriction there beyond being logged in)."""
    query = LoginHistory.query

    user_id = request.args.get("user_id", type=int)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    success = request.args.get("success")
    if success is not None:
        query = query.filter_by(success=success.lower() == "true")

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    query = query.order_by(LoginHistory.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        login_history=[i.to_dict() for i in items],
        pagination={"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page if per_page else 0},
    ), 200
