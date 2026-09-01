from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from ..audit.service import log_action
from ..extensions import db
from ..models import UserSession, utcnow
from ..utils import get_or_404
from . import service

bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")


@bp.get("")
@jwt_required()
def list_sessions():
    """Lists the caller's own active sessions. An admin may pass
    ?user_id=<id> to inspect another user's sessions (e.g. before
    deciding to revoke one) — this is the only admin-scoped read here;
    revocation itself goes through DELETE /<id> below, which already
    lets an admin target any user's session."""
    identity = int(get_jwt_identity())
    role = get_jwt().get("role")
    target_user_id = identity
    if role == "admin":
        requested = request.args.get("user_id", type=int)
        if requested is not None:
            target_user_id = requested

    current_sid = get_jwt().get("sid") if target_user_id == identity else None
    now = utcnow()
    sessions = (
        UserSession.query.filter_by(user_id=target_user_id, revoked_at=None)
        .filter(UserSession.expires_at > now)
        .order_by(UserSession.last_seen_at.desc())
        .all()
    )
    return jsonify(sessions=[s.to_dict(is_current=(s.refresh_jti == current_sid)) for s in sessions]), 200


@bp.delete("/<int:session_id>")
@jwt_required()
def revoke_one(session_id):
    session = get_or_404(UserSession, session_id)
    identity = int(get_jwt_identity())
    role = get_jwt().get("role")
    if session.user_id != identity and role != "admin":
        return jsonify(error="Forbidden"), 403

    if session.revoked_at is None:
        service.revoke_session(session)
        log_action(identity, "revoke", "session", session.id, before={"user_id": session.user_id})
        db.session.commit()
    return "", 204


@bp.post("/revoke-others")
@jwt_required()
def revoke_others():
    """Signs out every other active session for the caller while leaving
    the session that made this request untouched — the "sid" claim on
    the access token (set at login time, see auth/routes.py) is how the
    current session is identified without the caller having to name it."""
    identity = int(get_jwt_identity())
    current_sid = get_jwt().get("sid")
    sessions = UserSession.query.filter_by(user_id=identity, revoked_at=None).all()
    count = 0
    for session in sessions:
        if session.refresh_jti == current_sid:
            continue
        service.revoke_session(session)
        count += 1

    if count:
        log_action(identity, "revoke_others", "session", identity, after={"revoked_count": count})
    db.session.commit()
    return jsonify(revoked_count=count), 200


@bp.post("/revoke-all")
@jwt_required()
def revoke_all():
    identity = int(get_jwt_identity())
    sessions = UserSession.query.filter_by(user_id=identity, revoked_at=None).all()
    count = 0
    for session in sessions:
        service.revoke_session(session)
        count += 1

    if count:
        log_action(identity, "revoke_all", "session", identity, after={"revoked_count": count})
    db.session.commit()
    return jsonify(revoked_count=count), 200
