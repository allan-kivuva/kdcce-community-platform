import secrets
from datetime import timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from jwt.exceptions import PyJWTError
from marshmallow import ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

from ..audit.service import log_action
from ..extensions import db, limiter
from ..login_history import service as login_history
from ..models import RevokedToken, TotpRecoveryCode, TwoFactorChallenge, User, UserSession, VolunteerProfile, utcnow
from ..sessions import service as session_service
from .decorators import roles_required
from .schemas import RegisterSchema, LoginSchema
from .totp_service import build_otpauth_uri, generate_recovery_codes, generate_secret, verify_totp

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

register_schema = RegisterSchema()
login_schema = LoginSchema()

TWO_FACTOR_CHALLENGE_TTL = timedelta(minutes=5)


def _as_naive_utc(dt):
    """SQLite does not reliably round-trip a DateTime(timezone=True)
    column's tzinfo across a session boundary — see the identical helper
    in announcements/service.py and volunteer_hours/service.py. Applied
    here so a challenge's expires_at (read back from the DB, often
    naive) never gets compared directly against a freshly-computed
    utcnow() (always aware)."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo is not None else dt


def _identity_claims(user, sid=None):
    # Encoded straight into the JWT so every protected route can trust
    # req.user's role/id without a DB hit — but the id itself is what
    # `get_jwt_identity()` returns, never something the client supplies.
    # "sid" (session id) is the jti of this token's sibling refresh
    # token — how "sign out other devices" recognizes which session made
    # the current request without the caller having to name it.
    claims = {"role": user.role}
    if sid is not None:
        claims["sid"] = sid
    return claims


def _issue_tokens_and_finish_login(user, status_code=200):
    """The single place that mints a real token pair — reached either
    directly from login() (no 2FA required) or via a redeemed
    TwoFactorChallenge (verify-login/recovery). Always: creates the
    UserSession row for the new refresh token, records the successful
    LoginHistory entry, and stamps last_login_at, all in one commit."""
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=_identity_claims(user))
    _session, refresh_jti = session_service.create_session(user, refresh_token)
    access_token = create_access_token(identity=str(user.id), additional_claims=_identity_claims(user, sid=refresh_jti))

    user.last_login_at = utcnow()
    login_history.record_attempt(user, user.email, True)
    db.session.commit()
    return jsonify(user=user.to_dict(), access_token=access_token, refresh_token=refresh_token), status_code


def _create_two_factor_challenge(user):
    challenge = TwoFactorChallenge(
        user_id=user.id,
        token=secrets.token_urlsafe(32),
        expires_at=utcnow() + TWO_FACTOR_CHALLENGE_TTL,
    )
    db.session.add(challenge)
    return challenge


def _get_valid_challenge(token):
    if not token:
        return None
    challenge = TwoFactorChallenge.query.filter_by(token=token).first()
    if challenge is None or challenge.consumed_at is not None:
        return None
    if _as_naive_utc(challenge.expires_at) < _as_naive_utc(utcnow()):
        return None
    return challenge


@bp.post("/register")
@limiter.limit("10 per minute")
def register():
    payload = request.get_json(silent=True) or {}
    try:
        data = register_schema.load(payload)
    except ValidationError as err:
        return jsonify(error="Validation failed", details=err.messages), 400

    if User.query.filter_by(email=data["email"].lower()).first():
        return jsonify(error="An account with that email already exists"), 409

    user = User(name=data["name"].strip(), email=data["email"].lower(), role="volunteer")
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()  # assigns user.id without committing yet
    # Public self-signup always makes a volunteer, so it always gets a
    # volunteer profile too (status Pending until staff verify it) —
    # see app/volunteers/.
    db.session.add(VolunteerProfile(user_id=user.id))

    return _issue_tokens_and_finish_login(user, status_code=201)


@bp.post("/login")
@limiter.limit("10 per minute")
def login():
    payload = request.get_json(silent=True) or {}
    try:
        data = login_schema.load(payload)
    except ValidationError as err:
        return jsonify(error="Validation failed", details=err.messages), 400

    email = data["email"].lower()
    user = User.query.filter_by(email=email).first()

    if user is None or not user.check_password(data["password"]):
        login_history.record_attempt(user, email, False, "invalid_credentials")
        db.session.commit()
        return jsonify(error="Invalid email or password"), 401

    if not user.active or user.deleted_at is not None:
        login_history.record_attempt(user, email, False, "account_disabled")
        db.session.commit()
        return jsonify(error="This account has been disabled"), 403

    if user.totp_enabled:
        challenge = _create_two_factor_challenge(user)
        db.session.commit()
        return jsonify(two_factor_required=True, challenge_token=challenge.token), 200

    return _issue_tokens_and_finish_login(user)


@bp.post("/2fa/verify-login")
@limiter.limit("10 per minute")
def verify_login_2fa():
    payload = request.get_json(silent=True) or {}
    challenge = _get_valid_challenge(payload.get("challenge_token"))
    if challenge is None:
        return jsonify(error="Invalid or expired login challenge"), 401

    user = db.session.get(User, challenge.user_id)
    code = str(payload.get("code") or "")
    if user is None or not user.totp_enabled or not verify_totp(user.totp_secret, code):
        login_history.record_attempt(user, user.email if user else None, False, "invalid_otp")
        db.session.commit()
        return jsonify(error="Invalid verification code"), 401

    challenge.consumed_at = utcnow()
    return _issue_tokens_and_finish_login(user)


@bp.post("/2fa/recovery")
@limiter.limit("10 per minute")
def recovery_2fa():
    payload = request.get_json(silent=True) or {}
    challenge = _get_valid_challenge(payload.get("challenge_token"))
    if challenge is None:
        return jsonify(error="Invalid or expired login challenge"), 401

    user = db.session.get(User, challenge.user_id)
    recovery_code = str(payload.get("recovery_code") or "").strip()
    matched = None
    if user is not None and recovery_code:
        for candidate in TotpRecoveryCode.query.filter_by(user_id=user.id, used_at=None).all():
            if check_password_hash(candidate.code_hash, recovery_code):
                matched = candidate
                break

    if matched is None:
        login_history.record_attempt(user, user.email if user else None, False, "invalid_recovery_code")
        db.session.commit()
        return jsonify(error="Invalid recovery code"), 401

    matched.used_at = utcnow()
    challenge.consumed_at = utcnow()
    log_action(user.id, "recovery_code_used", "two_factor", user.id, after={"recovery_code_id": matched.id})
    return _issue_tokens_and_finish_login(user)


@bp.post("/2fa/setup")
@roles_required("admin")
def setup_2fa():
    """Generates a new pending secret and returns it once (base32 for
    manual entry, plus the otpauth:// URI the frontend renders as a QR
    code locally — never sent to any third-party QR service). Does NOT
    enable 2FA yet; that only happens once /2fa/verify-setup proves the
    admin actually captured a working code from it."""
    user = db.session.get(User, int(get_jwt_identity()))
    if user.totp_enabled:
        return jsonify(error="Two-factor authentication is already enabled"), 409

    secret = generate_secret()
    user.totp_secret = secret
    db.session.commit()
    return jsonify(secret=secret, otpauth_uri=build_otpauth_uri(secret, user.email)), 200


@bp.post("/2fa/verify-setup")
@roles_required("admin")
@limiter.limit("10 per minute")
def verify_setup_2fa():
    identity = int(get_jwt_identity())
    user = db.session.get(User, identity)
    if not user.totp_secret:
        return jsonify(error="Call /api/auth/2fa/setup first"), 400
    if user.totp_enabled:
        return jsonify(error="Two-factor authentication is already enabled"), 409

    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code") or "")
    if not verify_totp(user.totp_secret, code):
        return jsonify(error="Invalid verification code"), 400

    user.totp_enabled = True
    user.totp_confirmed_at = utcnow()
    # Clear out any codes left over from a prior enable/disable cycle
    # before generating a fresh set.
    TotpRecoveryCode.query.filter_by(user_id=user.id).delete()
    plaintext_codes = generate_recovery_codes()
    for code_str in plaintext_codes:
        db.session.add(TotpRecoveryCode(user_id=user.id, code_hash=generate_password_hash(code_str)))

    log_action(identity, "enable", "two_factor", user.id, after={"enabled": True})
    db.session.commit()
    # Recovery codes are returned in plaintext exactly this once — only
    # their hashes are ever stored, and this response is never logged.
    return jsonify(enabled=True, recovery_codes=plaintext_codes), 200


@bp.post("/2fa/disable")
@roles_required("admin")
def disable_2fa():
    """Requires the current password as reauthentication — 2FA can never
    be turned off by a bare authenticated request alone."""
    identity = int(get_jwt_identity())
    user = db.session.get(User, identity)
    if not user.totp_enabled:
        return jsonify(error="Two-factor authentication is not enabled"), 409

    payload = request.get_json(silent=True) or {}
    if not user.check_password(payload.get("password") or ""):
        return jsonify(error="Incorrect password"), 401

    user.totp_enabled = False
    user.totp_secret = None
    user.totp_confirmed_at = None
    TotpRecoveryCode.query.filter_by(user_id=user.id).delete()

    log_action(identity, "disable", "two_factor", user.id, after={"enabled": False})
    db.session.commit()
    return jsonify(enabled=False), 200


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify(error="User not found"), 404
    if not user.active or user.deleted_at is not None:
        # The refresh token is still cryptographically valid, but the
        # account behind it is not — mint no further access tokens.
        return jsonify(error="This account has been disabled"), 403

    refresh_jti = get_jwt()["jti"]
    session_service.touch_session(refresh_jti)
    access_token = create_access_token(identity=str(user.id), additional_claims=_identity_claims(user, sid=refresh_jti))
    db.session.commit()
    return jsonify(access_token=access_token), 200


@bp.post("/logout")
@jwt_required()
def logout():
    """Revokes the access token used to call this endpoint, plus the
    refresh token if the client sends one in the body. Both go into the
    same denylist (see RevokedToken / jwt.token_in_blocklist_loader) —
    from that point on, either token is rejected by every protected route
    even though it hasn't naturally expired yet."""
    db.session.add(RevokedToken(jti=get_jwt()["jti"]))

    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refresh_token")
    if refresh_token:
        try:
            refresh_claims = decode_token(refresh_token)
        except PyJWTError:
            refresh_claims = None
        if refresh_claims is not None and refresh_claims.get("type") == "refresh":
            jti = refresh_claims["jti"]
            # Guard against a double-insert (e.g. two tabs signing out with
            # the same refresh token) hitting the jti unique constraint —
            # unlike the access token above, this path isn't already
            # protected by the blocklist check happening at the decorator
            # level, since the refresh token was never used to authenticate
            # this request.
            if not RevokedToken.query.filter_by(jti=jti).first():
                db.session.add(RevokedToken(jti=jti))
            # Keep the session list honest — a logged-out refresh token
            # shouldn't still show as an "active" session.
            session_row = UserSession.query.filter_by(refresh_jti=jti).first()
            if session_row is not None and session_row.revoked_at is None:
                session_row.revoked_at = utcnow()

    db.session.commit()
    return "", 204


@bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify(error="User not found"), 404
    return jsonify(user=user.to_dict()), 200
