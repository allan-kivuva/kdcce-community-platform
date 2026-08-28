VALID_MESSAGE = {
    "name": "Grace M.",
    "email": "grace@example.com",
    "subject": "Volunteering interest",
    "message": "Hi, I would love to volunteer on weekends.",
}


def test_public_can_submit_message(client):
    resp = client.post("/api/inbox", json=VALID_MESSAGE)
    assert resp.status_code == 201
    body = resp.get_json()["message"]
    assert body["name"] == "Grace M."
    assert body["email"] == "grace@example.com"
    assert body["is_read"] is False


def test_is_read_from_client_is_ignored(client):
    resp = client.post("/api/inbox", json={**VALID_MESSAGE, "is_read": True})
    assert resp.status_code in (201, 400)
    if resp.status_code == 201:
        assert resp.get_json()["message"]["is_read"] is False


def test_rejects_missing_required_field(client):
    payload = {k: v for k, v in VALID_MESSAGE.items() if k != "message"}
    resp = client.post("/api/inbox", json=payload)
    assert resp.status_code == 400
    assert "message" in resp.get_json()["details"]


def test_rejects_invalid_email(client):
    resp = client.post("/api/inbox", json={**VALID_MESSAGE, "email": "not-an-email"})
    assert resp.status_code == 400
    assert "email" in resp.get_json()["details"]


def test_list_requires_auth(client):
    resp = client.get("/api/admin/inbox")
    assert resp.status_code == 401


def test_volunteer_cannot_list(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.get("/api/admin/inbox", headers=auth_header(token))
    assert resp.status_code == 403


def test_staff_can_list_submitted_messages(client, make_staff_user, auth_header):
    client.post("/api/inbox", json=VALID_MESSAGE)
    client.post("/api/inbox", json={**VALID_MESSAGE, "name": "Daniel K.", "email": "daniel@example.com"})
    _, token = make_staff_user("staff")
    resp = client.get("/api/admin/inbox", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["pagination"]["total"] == 2
    assert len(body["messages"]) == 2
    # newest first
    assert body["messages"][0]["name"] == "Daniel K."


def test_admin_can_list_submitted_messages(client, make_staff_user, auth_header):
    client.post("/api/inbox", json=VALID_MESSAGE)
    _, token = make_staff_user("admin")
    resp = client.get("/api/admin/inbox", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["pagination"]["total"] == 1


def test_unread_only_filter(client, make_staff_user, auth_header):
    client.post("/api/inbox", json=VALID_MESSAGE)
    client.post("/api/inbox", json={**VALID_MESSAGE, "name": "Daniel K.", "email": "daniel@example.com"})
    _, token = make_staff_user("staff")
    msg_id = client.get("/api/admin/inbox", headers=auth_header(token)).get_json()["messages"][0]["id"]
    client.patch(f"/api/admin/inbox/{msg_id}", json={"is_read": True}, headers=auth_header(token))

    resp = client.get("/api/admin/inbox?unread_only=true", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["pagination"]["total"] == 1


def test_pagination(client, make_staff_user, auth_header):
    for i in range(3):
        client.post("/api/inbox", json={**VALID_MESSAGE, "email": f"m{i}@example.com"})
    _, token = make_staff_user("staff")
    resp = client.get("/api/admin/inbox?per_page=2&page=1", headers=auth_header(token))
    body = resp.get_json()
    assert len(body["messages"]) == 2
    assert body["pagination"]["total"] == 3
    assert body["pagination"]["pages"] == 2


def test_staff_can_mark_read_and_unread(client, make_staff_user, auth_header):
    client.post("/api/inbox", json=VALID_MESSAGE)
    _, token = make_staff_user("staff")
    msg_id = client.get("/api/admin/inbox", headers=auth_header(token)).get_json()["messages"][0]["id"]

    resp = client.patch(f"/api/admin/inbox/{msg_id}", json={"is_read": True}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["message"]["is_read"] is True

    resp = client.patch(f"/api/admin/inbox/{msg_id}", json={"is_read": False}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["message"]["is_read"] is False


def test_volunteer_cannot_mark_read(client, make_user, make_staff_user, auth_header):
    client.post("/api/inbox", json=VALID_MESSAGE)
    _, staff_token = make_staff_user("staff")
    msg_id = client.get("/api/admin/inbox", headers=auth_header(staff_token)).get_json()["messages"][0]["id"]
    _, vol_token, _ = make_user()
    resp = client.patch(f"/api/admin/inbox/{msg_id}", json={"is_read": True}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_mark_read_missing_message_404(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.patch("/api/admin/inbox/999", json={"is_read": True}, headers=auth_header(token))
    assert resp.status_code == 404


def test_staff_can_delete_message(client, make_staff_user, auth_header):
    client.post("/api/inbox", json=VALID_MESSAGE)
    _, token = make_staff_user("staff")
    msg_id = client.get("/api/admin/inbox", headers=auth_header(token)).get_json()["messages"][0]["id"]

    resp = client.delete(f"/api/admin/inbox/{msg_id}", headers=auth_header(token))
    assert resp.status_code == 204

    resp = client.get("/api/admin/inbox", headers=auth_header(token))
    assert resp.get_json()["pagination"]["total"] == 0


def test_volunteer_cannot_delete(client, make_user, make_staff_user, auth_header):
    client.post("/api/inbox", json=VALID_MESSAGE)
    _, staff_token = make_staff_user("staff")
    msg_id = client.get("/api/admin/inbox", headers=auth_header(staff_token)).get_json()["messages"][0]["id"]
    _, vol_token, _ = make_user()
    resp = client.delete(f"/api/admin/inbox/{msg_id}", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_delete_missing_message_404(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.delete("/api/admin/inbox/999", headers=auth_header(token))
    assert resp.status_code == 404
