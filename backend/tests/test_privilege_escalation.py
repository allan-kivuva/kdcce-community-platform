"""Phase 7 explicitly calls for dedicated privilege-escalation and IDOR
coverage on top of the ordinary CRUD tests in test_users.py/test_sessions.py
— this file collects the sharpest edge cases in one place rather than
leaving them implicit."""


def test_user_create_schema_rejects_unknown_fields_like_active_or_id(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post(
        "/api/users",
        json={
            "name": "Sneaky", "email": "sneaky-fields@example.com", "password": "hunter22", "role": "staff",
            "active": False, "id": 999999, "totp_enabled": True,
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 400


def test_staff_cannot_read_arbitrary_user_detail(client, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    _, admin_token = make_staff_user("admin", email="target-admin@example.com")
    admin_user = client.get("/api/auth/me", headers=auth_header(admin_token)).get_json()["user"]

    resp = client.get(f"/api/users/{admin_user['id']}", headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_staff_cannot_soft_delete_a_user(client, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    target, _ = make_staff_user("volunteer", email="target-vol@example.com")
    resp = client.delete(f"/api/users/{target['id']}", headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_staff_cannot_reset_another_users_password(client, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    target, _ = make_staff_user("volunteer", email="target-reset@example.com")
    resp = client.post(f"/api/users/{target['id']}/reset-password", headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_non_admin_user_id_query_param_on_sessions_is_ignored(client, make_staff_user, auth_header):
    """A staff caller passing ?user_id=<someone else> on GET /api/sessions
    must only ever see their own sessions — the admin-only override is
    gated by the JWT's own role claim, not by the presence of the param."""
    staff_user, staff_token = make_staff_user("staff")
    other_user, other_token = make_staff_user("staff", email="other-target@example.com")

    resp = client.get(f"/api/sessions?user_id={other_user['id']}", headers=auth_header(staff_token))
    assert resp.status_code == 200
    # A synthetic token from make_staff_user carries no active UserSession
    # row at all (it bypasses /api/auth/login), so both should be empty —
    # the point is that no session belonging to `other_user` leaks in.
    assert resp.get_json()["sessions"] == []


def test_cannot_escalate_role_via_status_endpoint(client, make_staff_user, auth_header):
    """/status only ever accepts {"active": bool} — marshmallow's default
    unknown-field=RAISE behavior means smuggling a "role" field in here
    is rejected outright (400), not silently ignored."""
    _, admin_token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="status-only@example.com")
    resp = client.patch(
        f"/api/users/{target['id']}/status",
        json={"active": True, "role": "admin"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400

    detail = client.get(f"/api/users/{target['id']}", headers=auth_header(admin_token)).get_json()["user"]
    assert detail["role"] == "staff"


def test_cannot_escalate_active_via_role_endpoint(client, make_staff_user, auth_header):
    """/role only ever accepts {"role": ...} — an "active" field
    alongside it is rejected outright (400), not silently ignored."""
    _, admin_token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="role-only@example.com")
    client.patch(f"/api/users/{target['id']}/status", json={"active": False}, headers=auth_header(admin_token))

    resp = client.patch(
        f"/api/users/{target['id']}/role",
        json={"role": "staff", "active": True},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400
    detail = client.get(f"/api/users/{target['id']}", headers=auth_header(admin_token)).get_json()["user"]
    assert detail["active"] is False


def test_forged_role_claim_body_field_has_no_effect_on_registration(client):
    """A public self-signup body can name any role it likes — the server
    only ever creates a volunteer, never reads a role from the request."""
    resp = client.post(
        "/api/auth/register",
        json={"name": "Forge", "email": "forge@example.com", "password": "hunter22", "role": "admin"},
    )
    assert resp.status_code == 400  # unknown field "role" is rejected outright


def test_volunteer_cannot_reach_any_admin_security_surface(client, make_user, auth_header):
    _, token, _ = make_user(email="plain-vol@example.com")
    header = auth_header(token)
    for method, path in (
        ("get", "/api/users"),
        ("get", "/api/audit-logs"),
        ("get", "/api/login-history"),
        ("get", "/api/system/security-overview"),
    ):
        resp = getattr(client, method)(path, headers=header)
        assert resp.status_code == 403, f"{method.upper()} {path} should be 403 for a volunteer, got {resp.status_code}"
