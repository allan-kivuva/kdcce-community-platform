from flask import Blueprint, jsonify, request

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import AssistanceRequest, ElderlyMember, FollowUp, HomeVisit, User, VolunteerProfile

bp = Blueprint("search", __name__, url_prefix="/api/search")

# Admin/staff only — a volunteer has no elderly-record access anywhere
# else in this app (see Incident's docstring in models.py), so a search
# spanning elderly members would be a new leak, not a convenience. A
# volunteer's own assignment lists are already small enough not to need
# search (My Home Visits / My Assistance Requests).
_RESULT_LIMIT = 5


def _matches(*columns):
    like = f"%{request.args.get('q', '').strip()}%"
    return db.or_(*[c.ilike(like) for c in columns])


@bp.get("")
@roles_required("admin", "staff")
def search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify(error="Validation failed", details={"q": ["Must be at least 2 characters"]}), 400

    elderly = (
        ElderlyMember.query.filter(_matches(ElderlyMember.full_name, ElderlyMember.member_id))
        .order_by(ElderlyMember.full_name.asc()).limit(_RESULT_LIMIT).all()
    )
    volunteers = (
        db.session.query(VolunteerProfile).join(User, VolunteerProfile.user_id == User.id)
        .filter(_matches(User.name, User.email))
        .order_by(User.name.asc()).limit(_RESULT_LIMIT).all()
    )
    visits = (
        HomeVisit.query.join(ElderlyMember, HomeVisit.elderly_member_id == ElderlyMember.id)
        .filter(_matches(ElderlyMember.full_name))
        .order_by(HomeVisit.created_at.desc()).limit(_RESULT_LIMIT).all()
    )
    requests_ = (
        AssistanceRequest.query.join(ElderlyMember, AssistanceRequest.elderly_member_id == ElderlyMember.id)
        .filter(_matches(ElderlyMember.full_name))
        .order_by(AssistanceRequest.created_at.desc()).limit(_RESULT_LIMIT).all()
    )
    follow_ups = (
        FollowUp.query.join(ElderlyMember, FollowUp.elderly_member_id == ElderlyMember.id)
        .filter(_matches(ElderlyMember.full_name, FollowUp.reason))
        .order_by(FollowUp.created_at.desc()).limit(_RESULT_LIMIT).all()
    )

    return jsonify(results={
        "elderly_members": [m.to_dict() for m in elderly],
        "volunteers": [v.to_dict() for v in volunteers],
        "home_visits": [v.to_dict() for v in visits],
        "assistance_requests": [r.to_dict() for r in requests_],
        "follow_ups": [f.to_dict() for f in follow_ups],
    }), 200
