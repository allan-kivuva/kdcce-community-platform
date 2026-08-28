from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from ..models import AssistanceRequest, HomeVisit

bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")

# Purely a read-aggregation over the two existing scheduling fields
# (HomeVisit.scheduled_at, AssistanceRequest.scheduled_at) — no new model.
# Same role-scoping every other assignment-adjacent endpoint already
# uses: a volunteer only ever gets their own events, never another
# volunteer's, via the exact same assigned_to_id == identity filter.


@bp.get("")
@jwt_required()
def list_calendar():
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())

    visits_q = HomeVisit.query.filter(HomeVisit.scheduled_at.isnot(None))
    requests_q = AssistanceRequest.query.filter(AssistanceRequest.scheduled_at.isnot(None))

    if role == "volunteer":
        visits_q = visits_q.filter(HomeVisit.assigned_to_id == identity)
        requests_q = requests_q.filter(AssistanceRequest.assigned_to_id == identity)
    elif role not in ("admin", "staff"):
        return jsonify(error="Forbidden"), 403

    start = request.args.get("start")  # YYYY-MM-DD, optional
    end = request.args.get("end")
    if start:
        visits_q = visits_q.filter(HomeVisit.scheduled_at >= start)
        requests_q = requests_q.filter(AssistanceRequest.scheduled_at >= start)
    if end:
        visits_q = visits_q.filter(HomeVisit.scheduled_at <= end)
        requests_q = requests_q.filter(AssistanceRequest.scheduled_at <= end)

    events = [
        {
            "id": v.id, "type": "home_visit",
            "elderly_member_id": v.elderly_member_id, "elderly_member_name": v.elderly_member.full_name,
            "assigned_to_id": v.assigned_to_id, "assigned_to": v.assigned_to.name if v.assigned_to else None,
            "scheduled_at": v.scheduled_at.isoformat(), "status": v.status,
        }
        for v in visits_q.all()
    ] + [
        {
            "id": r.id, "type": "assistance_request",
            "elderly_member_id": r.elderly_member_id, "elderly_member_name": r.elderly_member.full_name,
            "assigned_to_id": r.assigned_to_id, "assigned_to": r.assigned_to.name if r.assigned_to else None,
            "scheduled_at": r.scheduled_at.isoformat(), "status": r.status,
        }
        for r in requests_q.all()
    ]
    events.sort(key=lambda e: e["scheduled_at"])
    return jsonify(events=events), 200
