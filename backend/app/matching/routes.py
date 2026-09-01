from flask import Blueprint, jsonify, request

from ..auth.decorators import roles_required
from ..models import ElderlyMember
from ..utils import get_or_404
from . import service

bp = Blueprint("matching", __name__, url_prefix="/api/matching")


@bp.get("/volunteers")
@roles_required("admin", "staff")
def match_volunteers():
    """Admin/staff only — recommendations, never an assignment. Assigning
    someone remains the existing, separate HomeVisit/AssistanceRequest
    PATCH action; nothing here writes to either table."""
    member_id = request.args.get("member_id", type=int)
    if member_id is None:
        return jsonify(error="Validation failed", details={"member_id": ["Required"]}), 400
    member = get_or_404(ElderlyMember, member_id)

    request_type = request.args.get("request_type")
    on_date = request.args.get("date")
    try:
        results = service.rank_volunteers(member, request_type=request_type, on_date=on_date)
    except ValueError:
        return jsonify(error="Validation failed", details={"date": ["Must be YYYY-MM-DD"]}), 400

    return jsonify(volunteers=results), 200
