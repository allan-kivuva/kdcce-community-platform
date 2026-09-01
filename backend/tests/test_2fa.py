import time

from app.auth.totp_service import totp_at
from app.extensions import db
from app.models import LoginHistory, TotpRecoveryCode, User


def _create_admin(email="admin2fa@example.com", password="hunter22"):
    user = User(name="Admin", email=email, role="admin")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, email, password="hunter22"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _enable_2fa(client, access_token):
    setup = client.post("/api/auth/2fa/setup", headers=_auth(access_token)).get_json()
    secret = setup["secret"]
    code = totp_at(secret, time.time())
    resp = client.post("/api/auth/2fa/verify-setup", json={"code": code}, headers=_auth(access_token))
    assert resp.status_code == 200, resp.get_json()
    return secret, resp.get_json()["recovery_codes"]


def test_setup_returns_secret_and_otpauth_uri(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    resp = client.post("/api/auth/2fa/setup", headers=_auth(access))
    assert resp.status_code == 200
    body = resp.get_json()
    assert "secret" in body and "otpauth_uri" in body
    assert body["otpauth_uri"].startswith("otpauth://totp/")


def test_setup_forbidden_for_staff_and_volunteer(client, make_staff_user, make_user, auth_header):
    _, staff_token = make_staff_user("staff")
    assert client.post("/api/auth/2fa/setup", headers=auth_header(staff_token)).status_code == 403
    _, vol_token, _ = make_user()
    assert client.post("/api/auth/2fa/setup", headers=auth_header(vol_token)).status_code == 403


def test_verify_setup_rejects_invalid_code(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    client.post("/api/auth/2fa/setup", headers=_auth(access))
    resp = client.post("/api/auth/2fa/verify-setup", json={"code": "000000"}, headers=_auth(access))
    assert resp.status_code == 400


def test_verify_setup_with_valid_code_enables_and_returns_recovery_codes(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    secret, recovery_codes = _enable_2fa(client, access)
    assert len(recovery_codes) == 8

    with app.app_context():
        refreshed = db.session.get(User, admin.id)
        assert refreshed.totp_enabled is True
        assert TotpRecoveryCode.query.filter_by(user_id=admin.id).count() == 8


def test_recovery_codes_are_stored_hashed_not_plaintext(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    _secret, recovery_codes = _enable_2fa(client, access)

    with app.app_context():
        stored = TotpRecoveryCode.query.filter_by(user_id=admin.id).all()
        stored_hashes = [row.code_hash for row in stored]
        for plaintext in recovery_codes:
            assert plaintext not in stored_hashes


def test_login_with_2fa_enabled_returns_challenge_not_tokens(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    _enable_2fa(client, access)

    resp = _login(client, admin.email)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("two_factor_required") is True
    assert "challenge_token" in body
    assert "access_token" not in body
    assert "refresh_token" not in body


def test_verify_login_with_valid_code_issues_tokens(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    secret, _codes = _enable_2fa(client, access)

    challenge_token = _login(client, admin.email).get_json()["challenge_token"]
    code = totp_at(secret, time.time())
    resp = client.post("/api/auth/2fa/verify-login", json={"challenge_token": challenge_token, "code": code})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "access_token" in body and "refresh_token" in body


def test_verify_login_with_invalid_code_fails_and_is_recorded(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    _enable_2fa(client, access)
    challenge_token = _login(client, admin.email).get_json()["challenge_token"]

    resp = client.post("/api/auth/2fa/verify-login", json={"challenge_token": challenge_token, "code": "000000"})
    assert resp.status_code == 401

    with app.app_context():
        rows = LoginHistory.query.filter_by(user_id=admin.id, failure_reason="invalid_otp").all()
        assert len(rows) == 1


def test_challenge_token_cannot_be_reused_after_success(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    secret, _codes = _enable_2fa(client, access)
    challenge_token = _login(client, admin.email).get_json()["challenge_token"]
    code = totp_at(secret, time.time())
    first = client.post("/api/auth/2fa/verify-login", json={"challenge_token": challenge_token, "code": code})
    assert first.status_code == 200

    second = client.post("/api/auth/2fa/verify-login", json={"challenge_token": challenge_token, "code": code})
    assert second.status_code == 401


def test_recovery_code_login_works_and_is_single_use(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    _secret, codes = _enable_2fa(client, access)

    challenge_token = _login(client, admin.email).get_json()["challenge_token"]
    resp = client.post("/api/auth/2fa/recovery", json={"challenge_token": challenge_token, "recovery_code": codes[0]})
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()

    # Same code cannot be used a second time, even against a fresh challenge.
    challenge_token_2 = _login(client, admin.email).get_json()["challenge_token"]
    resp2 = client.post("/api/auth/2fa/recovery", json={"challenge_token": challenge_token_2, "recovery_code": codes[0]})
    assert resp2.status_code == 401


def test_disable_requires_correct_password(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    _enable_2fa(client, access)

    resp = client.post("/api/auth/2fa/disable", json={"password": "wrong-password"}, headers=_auth(access))
    assert resp.status_code == 401

    with app.app_context():
        assert db.session.get(User, admin.id).totp_enabled is True


def test_disable_with_correct_password_disables_and_clears_recovery_codes(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    _enable_2fa(client, access)

    resp = client.post("/api/auth/2fa/disable", json={"password": "hunter22"}, headers=_auth(access))
    assert resp.status_code == 200
    assert resp.get_json()["enabled"] is False

    with app.app_context():
        refreshed = db.session.get(User, admin.id)
        assert refreshed.totp_enabled is False
        assert refreshed.totp_secret is None
        assert TotpRecoveryCode.query.filter_by(user_id=admin.id).count() == 0

    # Login now works without a 2FA challenge again.
    login_resp = _login(client, admin.email)
    assert "access_token" in login_resp.get_json()


def test_totp_secret_never_appears_in_any_user_response(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    _enable_2fa(client, access)

    me = client.get("/api/auth/me", headers=_auth(access)).get_json()["user"]
    assert "totp_secret" not in me
    assert me["two_factor_enabled"] is True


def test_2fa_verify_login_is_rate_limited(client, app):
    admin = _create_admin()
    access = _login(client, admin.email).get_json()["access_token"]
    _enable_2fa(client, access)
    challenge_token = _login(client, admin.email).get_json()["challenge_token"]

    statuses = [
        client.post("/api/auth/2fa/verify-login", json={"challenge_token": challenge_token, "code": "000000"}).status_code
        for _ in range(11)
    ]
    assert 429 in statuses
