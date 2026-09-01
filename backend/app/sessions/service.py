from datetime import datetime, timezone

from flask import request
from flask_jwt_extended import decode_token

from ..extensions import db
from ..models import RevokedToken, UserSession, utcnow


def create_session(user, refresh_token):
    """Called right after minting a refresh token (login/register/2FA
    verify) — decodes it once to pull its jti and real expiry, and
    records a UserSession row an owner can later see/revoke. Returns the
    jti so the caller can embed it as the "sid" claim on the sibling
    access token (see auth/routes.py:_identity_claims)."""
    decoded = decode_token(refresh_token)
    jti = decoded["jti"]
    expires_at = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    session = UserSession(
        user_id=user.id,
        refresh_jti=jti,
        expires_at=expires_at,
        ip_address=request.remote_addr,
        user_agent=(request.headers.get("User-Agent") or "")[:255],
    )
    db.session.add(session)
    return session, jti


def touch_session(refresh_jti):
    """Bumps last_seen_at when a refresh token is used to mint a new
    access token — the only signal available that the session is still
    in active use, short of tracking every single request."""
    session = UserSession.query.filter_by(refresh_jti=refresh_jti).first()
    if session is not None and session.revoked_at is None:
        session.last_seen_at = utcnow()
    return session


def revoke_session(session):
    """Marks the session revoked AND denylists its refresh_jti (the same
    RevokedToken table logout already uses) in one place, so the two can
    never drift apart — a session can't show as active while its
    underlying refresh token still works, or vice versa."""
    if session.revoked_at is not None:
        return
    session.revoked_at = utcnow()
    if not RevokedToken.query.filter_by(jti=session.refresh_jti).first():
        db.session.add(RevokedToken(jti=session.refresh_jti))
