import time

from app.volunteers.qr_service import issue_identity_token, verify_identity_token, QrTokenError


def _verified_volunteer(client, make_user, auth_header, admin_token, email="id-vol@example.com"):
    user, access_token, _ = make_user(email=email, name="ID Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


# ---------- Digital ID: self-only, correct state, private fields excluded ----------

def test_volunteer_can_view_own_digital_id(client, make_user, auth_header):
    _, token, _ = make_user(email="ownid@example.com", name="Own Id Person")
    resp = client.get("/api/volunteers/me/digital-id", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()["digital_id"]
    assert body["name"] == "Own Id Person"
    assert body["status"] == "Pending"
    assert body["volunteer_code"].startswith("KDCCE-VOL-")


def test_digital_id_excludes_email_and_phone(client, make_user, auth_header):
    _, token, _ = make_user(email="privateid@example.com")
    body = client.get("/api/volunteers/me/digital-id", headers=auth_header(token)).get_json()["digital_id"]
    assert "email" not in body
    assert "phone" not in body
    serialized = str(body)
    assert "privateid@example.com" not in serialized


def test_digital_id_reflects_verified_status(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    user, token = _verified_volunteer(client, make_user, auth_header, admin_token)
    body = client.get("/api/volunteers/me/digital-id", headers=auth_header(token)).get_json()["digital_id"]
    assert body["status"] == "Verified"


def test_digital_id_reflects_rejected_status(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    user, token, _ = make_user(email="rejectedid@example.com")
    vid = next(v for v in client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"] if v["email"] == "rejectedid@example.com")["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Rejected"}, headers=auth_header(admin_token))
    body = client.get("/api/volunteers/me/digital-id", headers=auth_header(token)).get_json()["digital_id"]
    assert body["status"] == "Rejected"


def test_unauthenticated_cannot_view_digital_id(client):
    assert client.get("/api/volunteers/me/digital-id").status_code == 401


def test_staff_or_admin_have_no_digital_id_of_their_own(client, make_staff_user, auth_header):
    """Staff/admin have no VolunteerProfile at all — same 404 as every
    other /me/* volunteer-only endpoint."""
    _, token = make_staff_user("staff")
    resp = client.get("/api/volunteers/me/digital-id", headers=auth_header(token))
    assert resp.status_code == 404


# ---------- QR token: unit-level (signature/expiry/tamper) ----------
# Needs an app context (SECRET_KEY comes from current_app.config) — the
# `app` fixture from conftest.py provides one, same as any other
# app-context-dependent unit test in this suite.

def test_issued_token_verifies_back_to_the_same_user_id(app):
    with app.app_context():
        token = issue_identity_token(42)
        assert verify_identity_token(token) == 42


def test_tampered_token_is_rejected(app):
    with app.app_context():
        token = issue_identity_token(42)
        tampered = token[:-1] + ("x" if token[-1] != "x" else "y")
        try:
            verify_identity_token(tampered)
            assert False, "expected QrTokenError"
        except QrTokenError:
            pass


def test_garbage_token_is_rejected(app):
    with app.app_context():
        try:
            verify_identity_token("not-a-real-token-at-all")
            assert False, "expected QrTokenError"
        except QrTokenError:
            pass


def test_expired_token_is_rejected(app, monkeypatch):
    import app.volunteers.qr_service as qr_service
    monkeypatch.setattr(qr_service, "_MAX_AGE_SECONDS", 0)
    with app.app_context():
        token = issue_identity_token(42)
        time.sleep(1.1)
        try:
            verify_identity_token(token)
            assert False, "expected QrTokenError"
        except QrTokenError as err:
            assert "expired" in err.message.lower()


# ---------- QR endpoints: route-level authorization ----------

def test_volunteer_can_generate_their_own_qr_token(client, make_user, auth_header):
    _, token, _ = make_user(email="genqr@example.com")
    resp = client.get("/api/volunteers/me/digital-id/qr-token", headers=auth_header(token))
    assert resp.status_code == 200
    assert "token" in resp.get_json()
    assert resp.get_json()["expires_in_seconds"] == 300


def test_admin_can_verify_a_valid_qr_token(client, make_user, make_staff_user, auth_header):
    user, token, _ = make_user(email="verifyqr@example.com", name="Verify QR Person")
    _, admin_token = make_staff_user("admin")
    qr_token = client.get("/api/volunteers/me/digital-id/qr-token", headers=auth_header(token)).get_json()["token"]

    resp = client.post("/api/volunteers/qr/verify", json={"token": qr_token}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["digital_id"]["name"] == "Verify QR Person"


def test_staff_can_verify_a_valid_qr_token(client, make_user, make_staff_user, auth_header):
    user, token, _ = make_user(email="staffverifyqr@example.com")
    _, staff_token = make_staff_user("staff")
    qr_token = client.get("/api/volunteers/me/digital-id/qr-token", headers=auth_header(token)).get_json()["token"]
    resp = client.post("/api/volunteers/qr/verify", json={"token": qr_token}, headers=auth_header(staff_token))
    assert resp.status_code == 200


def test_volunteer_cannot_use_the_admin_verify_endpoint(client, make_user, auth_header):
    """Even a token holder themselves can't call the verify endpoint — a
    volunteer scanning/verifying is not the intended flow (staff/admin
    scan a volunteer's ID, not the other way around)."""
    _, token, _ = make_user(email="novolverify@example.com")
    qr_token = client.get("/api/volunteers/me/digital-id/qr-token", headers=auth_header(token)).get_json()["token"]
    resp = client.post("/api/volunteers/qr/verify", json={"token": qr_token}, headers=auth_header(token))
    assert resp.status_code == 403


def test_verify_rejects_a_tampered_token(client, make_user, make_staff_user, auth_header):
    _, token, _ = make_user(email="tamperroute@example.com")
    _, admin_token = make_staff_user("admin")
    qr_token = client.get("/api/volunteers/me/digital-id/qr-token", headers=auth_header(token)).get_json()["token"]
    tampered = qr_token[:-2] + "zz"

    resp = client.post("/api/volunteers/qr/verify", json={"token": tampered}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_verify_rejects_an_expired_token(client, make_user, make_staff_user, auth_header, monkeypatch):
    import app.volunteers.qr_service as qr_service
    _, token, _ = make_user(email="expireroute@example.com")
    _, admin_token = make_staff_user("admin")
    qr_token = client.get("/api/volunteers/me/digital-id/qr-token", headers=auth_header(token)).get_json()["token"]

    monkeypatch.setattr(qr_service, "_MAX_AGE_SECONDS", 0)
    time.sleep(1.1)
    resp = client.post("/api/volunteers/qr/verify", json={"token": qr_token}, headers=auth_header(admin_token))
    assert resp.status_code == 400
    assert "expired" in resp.get_json()["error"].lower()


def test_verify_reused_still_valid_token_twice_both_succeed_readonly(client, make_user, make_staff_user, auth_header):
    """This verification is deliberately read-only (see qr_service's own
    docstring) — replaying a still-valid token within its window just
    re-confirms the same identity information again, no state changes,
    so there is nothing for a second verification within the window to
    corrupt or double-spend. Confirms that design choice holds: the
    second call succeeds identically, not rejected as a "used" token."""
    user, token, _ = make_user(email="replay@example.com")
    _, admin_token = make_staff_user("admin")
    qr_token = client.get("/api/volunteers/me/digital-id/qr-token", headers=auth_header(token)).get_json()["token"]

    first = client.post("/api/volunteers/qr/verify", json={"token": qr_token}, headers=auth_header(admin_token))
    second = client.post("/api/volunteers/qr/verify", json={"token": qr_token}, headers=auth_header(admin_token))
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()["digital_id"] == second.get_json()["digital_id"]


def test_verify_returns_404_if_volunteer_no_longer_exists(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    fake_token = issue_identity_token(999999)
    resp = client.post("/api/volunteers/qr/verify", json={"token": fake_token}, headers=auth_header(admin_token))
    assert resp.status_code == 404


def test_unauthenticated_cannot_verify_qr(client):
    assert client.post("/api/volunteers/qr/verify", json={"token": "x"}).status_code == 401
