import time

from app.auth.totp_service import totp_at


def test_security_overview_admin_only(client, make_staff_user, make_user, auth_header):
    _, staff_token = make_staff_user("staff")
    assert client.get("/api/system/security-overview", headers=auth_header(staff_token)).status_code == 403
    _, vol_token, _ = make_user()
    assert client.get("/api/system/security-overview", headers=auth_header(vol_token)).status_code == 403


def test_unauthenticated_cannot_view_security_overview(client):
    assert client.get("/api/system/security-overview").status_code == 401


def test_security_overview_shape(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/system/security-overview", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    for key in (
        "api_status", "db_connected", "recent_failed_logins", "active_session_count",
        "recent_critical_events", "disabled_account_count", "admin_2fa_coverage", "commit",
    ):
        assert key in body
    assert body["db_connected"] is True


def test_security_overview_never_exposes_secrets(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/system/security-overview", headers=auth_header(token))
    body_text = resp.get_data(as_text=True)
    for forbidden in ("SECRET_KEY", "JWT_SECRET_KEY", "password", "totp_secret", "DATABASE_URL"):
        assert forbidden not in body_text


def test_security_overview_counts_disabled_accounts(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="disabled-for-overview@example.com")
    client.patch(f"/api/users/{target['id']}/status", json={"active": False}, headers=auth_header(token))

    resp = client.get("/api/system/security-overview", headers=auth_header(token))
    assert resp.get_json()["disabled_account_count"] >= 1


def test_security_overview_reflects_admin_2fa_coverage(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    before = client.get("/api/system/security-overview", headers=auth_header(token)).get_json()["admin_2fa_coverage"]

    setup = client.post("/api/auth/2fa/setup", headers=auth_header(token)).get_json()
    code = totp_at(setup["secret"], time.time())
    client.post("/api/auth/2fa/verify-setup", json={"code": code}, headers=auth_header(token))

    after = client.get("/api/system/security-overview", headers=auth_header(token)).get_json()["admin_2fa_coverage"]
    assert after["enabled"] == before["enabled"] + 1
    assert after["total"] == before["total"]
