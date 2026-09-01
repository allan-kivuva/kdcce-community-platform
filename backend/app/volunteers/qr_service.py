from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

# A dedicated salt namespaces this signer from any other itsdangerous use
# in the app (there is none today, but this is required by itsdangerous's
# own API regardless, and is cheap, standard practice). Signed with the
# app's existing SECRET_KEY — no new secret to manage/rotate.
_SALT = "volunteer-digital-id-qr"
_MAX_AGE_SECONDS = 5 * 60  # short-lived on purpose — this is an identity
# check, not a login session; a token good for hours would be a real
# credential worth stealing, one good for 5 minutes only proves "this QR
# was generated recently by someone who could reach the volunteer's own
# authenticated session."


class QrTokenError(Exception):
    """Raised for any invalid/expired/malformed token — routes catch this
    and turn it into the app's standard 400 shape, same pattern as every
    other *Error class in this app."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_SALT)


def issue_identity_token(user_id):
    """A signed, time-limited token proving "this is volunteer <user_id>,
    as verified by this server, issued just now." Contains only what's
    needed to look the volunteer back up server-side — no name, no
    status, no role: the verify endpoint re-reads all of that fresh from
    the database rather than trusting anything embedded in the token
    itself, so a stale token can never carry stale identity claims."""
    return _serializer().dumps({"volunteer_user_id": user_id, "purpose": "identity"})


def verify_identity_token(token):
    """Checks signature + expiry (itsdangerous raises on either failure)
    and the purpose tag (defense in depth against a token minted for some
    future different purpose being replayed here). Returns the encoded
    user id on success; never trusts the payload beyond that one id —
    the caller looks up everything else fresh."""
    try:
        payload = _serializer().loads(token, max_age=_MAX_AGE_SECONDS)
    except SignatureExpired:
        raise QrTokenError("This code has expired — ask the volunteer to generate a new one")
    except BadSignature:
        raise QrTokenError("This code is invalid")
    if not isinstance(payload, dict) or payload.get("purpose") != "identity":
        raise QrTokenError("This code is invalid")
    return payload["volunteer_user_id"]
