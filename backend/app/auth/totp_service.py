"""RFC 6238 TOTP + RFC 4226 HOTP, implemented against the standard library
only (hmac/hashlib/struct/base64/secrets) — deliberately no pyotp/qrcode
dependency. The QR image itself is rendered client-side from the
otpauth:// URI this module returns (see frontend 2FA setup), so the
secret is never sent to any third-party QR-rendering service."""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

DIGITS = 6
PERIOD = 30
VALID_WINDOW = 1  # +/- one 30s step, tolerates minor clock drift


def generate_secret():
    """20 random bytes (160 bits), base32-encoded — the standard TOTP
    secret size used by every authenticator app."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _decode_secret(secret_b32):
    # Authenticator apps and users commonly strip the '=' padding when
    # copying a secret by hand; re-pad to a multiple of 8 before decoding.
    raw = secret_b32.strip().upper().replace(" ", "")
    padding = "=" * ((8 - len(raw) % 8) % 8)
    return base64.b32decode(raw + padding, casefold=True)


def _hotp(secret_bytes, counter, digits=DIGITS):
    counter_bytes = struct.pack(">Q", counter)
    digest = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code_int).zfill(digits)


def totp_at(secret_b32, at, period=PERIOD, digits=DIGITS):
    counter = int(at // period)
    return _hotp(_decode_secret(secret_b32), counter, digits)


def verify_totp(secret_b32, code, valid_window=VALID_WINDOW):
    """Constant-time compare across a small window of adjacent time
    steps, so a code from just before/after a 30s boundary still works."""
    if not secret_b32 or not code or not code.isdigit() or len(code) != DIGITS:
        return False
    now = time.time()
    for offset in range(-valid_window, valid_window + 1):
        expected = totp_at(secret_b32, now + offset * PERIOD)
        if hmac.compare_digest(expected, code):
            return True
    return False


def build_otpauth_uri(secret_b32, email, issuer="KDCCE"):
    label = quote(f"{issuer}:{email}")
    return (
        f"otpauth://totp/{label}?secret={secret_b32}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={PERIOD}"
    )


def generate_recovery_codes(count=8):
    """Plaintext codes — returned to the caller exactly once. The caller
    is responsible for hashing each one before storing it."""
    return [f"{secrets.token_hex(5)}-{secrets.token_hex(5)}" for _ in range(count)]
