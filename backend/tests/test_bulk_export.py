from app.models import AuditLog


def _member(client, token, auth_header, name="Mary Achieng"):
    return client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token)).get_json()["member"]


def test_export_specific_ids_returns_only_those_members(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _member(client, token, auth_header, "Alice Wambui")
    m2 = _member(client, token, auth_header, "John Otieno")
    m3 = _member(client, token, auth_header, "Someone Else")  # unrelated third member

    resp = client.post("/api/elderly/export", json={"ids": [m1["id"], m2["id"]]}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    text = resp.get_data(as_text=True)
    assert "Alice Wambui" in text
    assert "John Otieno" in text
    assert "Someone Else" not in text


def test_export_with_empty_ids_exports_every_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    _member(client, token, auth_header, "Alice Wambui")
    _member(client, token, auth_header, "John Otieno")

    resp = client.post("/api/elderly/export", json={"ids": []}, headers=auth_header(token))
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Alice Wambui" in text
    assert "John Otieno" in text


def test_export_with_no_body_exports_every_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    _member(client, token, auth_header, "Alice Wambui")
    _member(client, token, auth_header, "John Otieno")

    resp = client.post("/api/elderly/export", headers=auth_header(token))
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "Alice Wambui" in text
    assert "John Otieno" in text


def test_export_sanitizes_formula_injection_in_full_name(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    dangerous_name = "=cmd|'/c calc'!A1"
    member = _member(client, token, auth_header, dangerous_name)
    assert member["full_name"] == dangerous_name  # accepted as plain text — schema only checks length

    resp = client.post("/api/elderly/export", json={"ids": [member["id"]]}, headers=auth_header(token))
    text = resp.get_data(as_text=True)
    assert "'" + dangerous_name in text  # leading apostrophe prepended
    assert "\n" + dangerous_name not in text  # never appears as a bare, unprefixed formula cell


# ---------- Access control ----------

def test_volunteer_cannot_export(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/elderly/export", json={"ids": []}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_export(client):
    resp = client.post("/api/elderly/export", json={"ids": []})
    assert resp.status_code == 401


# ---------- Audit logging ----------

def test_export_creates_audit_log_row(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _member(client, token, auth_header, "Alice Wambui")
    m2 = _member(client, token, auth_header, "John Otieno")

    resp = client.post("/api/elderly/export", json={"ids": [m1["id"], m2["id"]]}, headers=auth_header(token))
    assert resp.status_code == 200

    logs = AuditLog.query.filter_by(resource_type="elderly_member", action="export").all()
    assert len(logs) == 1
    assert logs[0].resource_id == 2
