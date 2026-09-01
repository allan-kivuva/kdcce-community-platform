def test_admin_only_can_list_audit_logs(client, make_staff_user, make_user, auth_header):
    _, staff_token = make_staff_user("staff")
    assert client.get("/api/audit-logs", headers=auth_header(staff_token)).status_code == 403
    _, vol_token, _ = make_user()
    assert client.get("/api/audit-logs", headers=auth_header(vol_token)).status_code == 403


def test_unauthenticated_cannot_list_audit_logs(client):
    assert client.get("/api/audit-logs").status_code == 401


def test_sensitive_action_creates_an_audit_row(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post(
        "/api/users",
        json={"name": "Auditable", "email": "auditable@example.com", "password": "hunter22", "role": "staff"},
        headers=auth_header(token),
    ).get_json()["user"]

    resp = client.get(f"/api/audit-logs?resource_type=user&resource_id={created['id']}", headers=auth_header(token))
    assert resp.status_code == 200
    rows = resp.get_json()["audit_logs"]
    assert any(r["action"] == "create" and r["resource_type"] == "user" for r in rows)


def test_audit_log_detail_endpoint_returns_before_after(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="rolechange@example.com")
    client.patch(f"/api/users/{target['id']}/role", json={"role": "admin"}, headers=auth_header(token))

    listed = client.get("/api/audit-logs?resource_type=user&action=role_change", headers=auth_header(token)).get_json()["audit_logs"]
    log_id = listed[0]["id"]
    resp = client.get(f"/api/audit-logs/{log_id}", headers=auth_header(token))
    assert resp.status_code == 200
    entry = resp.get_json()["audit_log"]
    assert entry["before"] == {"role": "staff"}
    assert entry["after"] == {"role": "admin"}


def test_audit_log_detail_forbidden_for_non_admin(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="rc2@example.com")
    client.patch(f"/api/users/{target['id']}/role", json={"role": "admin"}, headers=auth_header(admin_token))
    log_id = client.get("/api/audit-logs", headers=auth_header(admin_token)).get_json()["audit_logs"][0]["id"]

    _, staff_token = make_staff_user("staff", email="peeker@example.com")
    resp = client.get(f"/api/audit-logs/{log_id}", headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_filter_by_actor_id(client, make_staff_user, auth_header):
    admin_user, admin_token = make_staff_user("admin")
    client.post(
        "/api/users",
        json={"name": "By Actor", "email": "byactor@example.com", "password": "hunter22", "role": "staff"},
        headers=auth_header(admin_token),
    )
    resp = client.get(f"/api/audit-logs?actor_id={admin_user['id']}", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert len(resp.get_json()["audit_logs"]) >= 1
    assert all(r["actor"] for r in resp.get_json()["audit_logs"])


def test_filter_by_action(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="statuschange@example.com")
    client.patch(f"/api/users/{target['id']}/status", json={"active": False}, headers=auth_header(admin_token))

    resp = client.get("/api/audit-logs?action=deactivate", headers=auth_header(admin_token))
    rows = resp.get_json()["audit_logs"]
    assert len(rows) >= 1
    assert all(r["action"] == "deactivate" for r in rows)


def test_no_sensitive_secrets_ever_appear_in_audit_rows(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    client.post(
        "/api/users",
        json={"name": "No Secrets", "email": "nosecrets@example.com", "password": "hunter22", "role": "staff"},
        headers=auth_header(admin_token),
    )
    resp = client.get("/api/audit-logs", headers=auth_header(admin_token))
    body_text = resp.get_data(as_text=True)
    assert "hunter22" not in body_text
    assert "password" not in body_text.lower()
