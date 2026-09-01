from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from ..models import Achievement

bp = Blueprint("achievements", __name__, url_prefix="/api/achievements")


@bp.get("")
@jwt_required()
def list_achievements():
    """The full definition set — any authenticated user (a volunteer sees
    this via their own achievements/upcoming view already; admin/staff
    need it to build the recognition picker). Read-only: there is no
    create/edit endpoint in this phase — the starter set is seeded once
    by its own migration (see e29a3d056e47) and isn't expected to change
    without a deliberate follow-up (see the final report's deferred
    items)."""
    achievements = Achievement.query.order_by(Achievement.category.asc(), Achievement.name.asc()).all()
    return jsonify(achievements=[a.to_dict() for a in achievements]), 200
