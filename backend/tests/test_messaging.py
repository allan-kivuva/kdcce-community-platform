def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com", name="Vera Volunteer"):
    user, access_token, _ = make_user(email=email, name=name)
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


# ---------- Creating a conversation ----------

def test_volunteer_can_message_staff(client, make_user, make_staff_user, auth_header):
    admin, admin_token = make_staff_user("admin")
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.post(
        "/api/messages/conversations",
        json={"recipient_id": admin["id"], "body": "Hello, I have a question."},
        headers=auth_header(vol_token),
    )
    assert resp.status_code == 201
    body = resp.get_json()["conversation"]
    assert body["other_user"]["role"] == "admin"
    assert body["messages"][0]["body"] == "Hello, I have a question."


def test_staff_can_message_volunteer(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, _, _ = make_user(email="pendingvol@example.com")

    resp = client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": "Welcome!"}, headers=auth_header(staff_token))
    assert resp.status_code == 201
    assert resp.get_json()["conversation"]["other_user"]["id"] == vol["id"]


def test_volunteer_cannot_message_another_volunteer(client, make_user, auth_header):
    _, tok_a, _ = make_user(email="vola@example.com")
    vol_b, _, _ = make_user(email="volb@example.com")

    resp = client.post("/api/messages/conversations", json={"recipient_id": vol_b["id"], "body": "Hi"}, headers=auth_header(tok_a))
    assert resp.status_code == 400


def test_cannot_message_self(client, make_staff_user, auth_header):
    admin, admin_token = make_staff_user("admin")
    resp = client.post("/api/messages/conversations", json={"recipient_id": admin["id"], "body": "Hi me"}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_cannot_message_nonexistent_user(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    resp = client.post("/api/messages/conversations", json={"recipient_id": 999999, "body": "Hi"}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_conversation_between_same_pair_is_reused_not_duplicated(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, vol_token, _ = make_user(email="reuse@example.com")

    r1 = client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": "First"}, headers=auth_header(staff_token))
    conv_id_1 = r1.get_json()["conversation"]["id"]

    staff_user_id = next(u["id"] for u in client.get("/api/messages/recipients", headers=auth_header(vol_token)).get_json()["recipients"])
    r2 = client.post("/api/messages/conversations", json={"recipient_id": staff_user_id, "body": "Reply"}, headers=auth_header(vol_token))
    conv_id_2 = r2.get_json()["conversation"]["id"]

    assert conv_id_1 == conv_id_2
    assert len(r2.get_json()["conversation"]["messages"]) == 2


def test_staff_can_message_another_staff_member(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    other_staff, _ = make_staff_user("staff", email="colleague@example.com")

    resp = client.post("/api/messages/conversations", json={"recipient_id": other_staff["id"], "body": "Meeting at 3?"}, headers=auth_header(admin_token))
    assert resp.status_code == 201


# ---------- Access control / IDOR ----------

def test_non_participant_cannot_view_conversation(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, _, _ = make_user(email="ownerofconvo@example.com")
    conv_id = client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": "Hi"}, headers=auth_header(staff_token)).get_json()["conversation"]["id"]

    _, outsider_token, _ = make_user(email="outsider@example.com")
    resp = client.get(f"/api/messages/conversations/{conv_id}", headers=auth_header(outsider_token))
    assert resp.status_code == 404


def test_nonexistent_conversation_id_returns_404_not_leaked(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    resp = client.get("/api/messages/conversations/999999", headers=auth_header(admin_token))
    assert resp.status_code == 404


def test_non_participant_cannot_send_message_into_conversation(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, _, _ = make_user(email="ownerof2@example.com")
    conv_id = client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": "Hi"}, headers=auth_header(staff_token)).get_json()["conversation"]["id"]

    _, outsider_token, _ = make_user(email="outsider2@example.com")
    resp = client.post(f"/api/messages/conversations/{conv_id}/messages", json={"body": "sneaky"}, headers=auth_header(outsider_token))
    assert resp.status_code == 404


def test_unauthenticated_cannot_access_messaging(client):
    assert client.get("/api/messages/conversations").status_code == 401
    assert client.post("/api/messages/conversations", json={"recipient_id": 1, "body": "hi"}).status_code == 401


# ---------- Sending / listing / unread state ----------

def test_send_follow_up_message_and_notifies_recipient(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, vol_token, _ = make_user(email="notifyme@example.com")
    conv_id = client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": "Hi"}, headers=auth_header(staff_token)).get_json()["conversation"]["id"]

    resp = client.post(f"/api/messages/conversations/{conv_id}/messages", json={"body": "Follow-up"}, headers=auth_header(staff_token))
    assert resp.status_code == 201

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Direct Message" for n in notifications)


def test_empty_message_body_rejected(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, _, _ = make_user(email="emptybody@example.com")
    resp = client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": ""}, headers=auth_header(staff_token))
    assert resp.status_code == 400


def test_unread_count_and_mark_read(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, vol_token, _ = make_user(email="unreadflow@example.com")
    conv_id = client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": "Hi there"}, headers=auth_header(staff_token)).get_json()["conversation"]["id"]

    resp = client.get("/api/messages/unread-count", headers=auth_header(vol_token))
    assert resp.get_json()["unread_count"] == 1

    client.patch(f"/api/messages/conversations/{conv_id}/read", headers=auth_header(vol_token))
    resp = client.get("/api/messages/unread-count", headers=auth_header(vol_token))
    assert resp.get_json()["unread_count"] == 0

    # A second message after read pushes the count back up
    client.post(f"/api/messages/conversations/{conv_id}/messages", json={"body": "still there?"}, headers=auth_header(staff_token))
    resp = client.get("/api/messages/unread-count", headers=auth_header(vol_token))
    assert resp.get_json()["unread_count"] == 1

    # The sender never sees their own message as unread
    resp = client.get("/api/messages/unread-count", headers=auth_header(staff_token))
    assert resp.get_json()["unread_count"] == 0


def test_conversation_list_shows_last_message_and_unread_flag(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, vol_token, _ = make_user(email="listflow@example.com")
    client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": "Hello"}, headers=auth_header(staff_token))

    resp = client.get("/api/messages/conversations", headers=auth_header(vol_token))
    assert resp.status_code == 200
    conversations = resp.get_json()["conversations"]
    assert len(conversations) == 1
    assert conversations[0]["last_message"]["body"] == "Hello"
    assert conversations[0]["unread_count"] == 1
    assert conversations[0]["other_user"]["role"] == "staff"


# ---------- Recipients & templates ----------

def test_volunteer_recipients_only_lists_staff_and_admin(client, make_user, make_staff_user, auth_header):
    make_staff_user("admin")
    make_staff_user("staff", email="s2@example.com")
    make_user(email="othervol@example.com")
    _, vol_token, _ = make_user(email="requester@example.com")

    resp = client.get("/api/messages/recipients", headers=auth_header(vol_token))
    roles = {r["role"] for r in resp.get_json()["recipients"]}
    assert roles.issubset({"admin", "staff"})


def test_admin_recipients_includes_volunteers_and_staff(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    make_staff_user("staff", email="s3@example.com")
    make_user(email="vfr@example.com")

    resp = client.get("/api/messages/recipients", headers=auth_header(admin_token))
    roles = {r["role"] for r in resp.get_json()["recipients"]}
    assert "volunteer" in roles
    assert "staff" in roles


def test_templates_are_admin_staff_only(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="notemplates@example.com")

    assert client.get("/api/messages/templates", headers=auth_header(admin_token)).status_code == 200
    assert client.get("/api/messages/templates", headers=auth_header(vol_token)).status_code == 403


# ---------- Unresolved queue ----------

def test_unresolved_detects_volunteer_waiting_and_clears_on_reply(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    vol, vol_token, _ = make_user(email="waiting@example.com")

    # Staff opens the thread first (so the conversation exists), then the
    # volunteer sends the message that should be "waiting for reply".
    conv_id = client.post("/api/messages/conversations", json={"recipient_id": vol["id"], "body": "Welcome"}, headers=auth_header(staff_token)).get_json()["conversation"]["id"]
    client.post(f"/api/messages/conversations/{conv_id}/messages", json={"body": "I have a question about my schedule"}, headers=auth_header(vol_token))

    resp = client.get("/api/messages/unresolved", headers=auth_header(staff_token))
    assert resp.status_code == 200
    unresolved = resp.get_json()["unresolved"]
    assert any(u["conversation_id"] == conv_id for u in unresolved)

    client.post(f"/api/messages/conversations/{conv_id}/messages", json={"body": "Sure, here's the schedule"}, headers=auth_header(staff_token))
    resp = client.get("/api/messages/unresolved", headers=auth_header(staff_token))
    assert not any(u["conversation_id"] == conv_id for u in resp.get_json()["unresolved"])


def test_unresolved_is_admin_staff_only(client, make_user, auth_header):
    _, vol_token, _ = make_user(email="nounresolved@example.com")
    resp = client.get("/api/messages/unresolved", headers=auth_header(vol_token))
    assert resp.status_code == 403


# ---------- Assignment-conversation summary ----------

def test_assignment_conversations_lists_a_visit_with_messages(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    member = _register_member(client, staff_token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Checkup"}, headers=auth_header(staff_token)).get_json()["visit"]
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, staff_token, email="assignvol@example.com")
    client.patch(f"/api/home-visits/{visit['id']}", json={"assigned_to_id": vol["id"]}, headers=auth_header(staff_token))

    client.post(f"/api/home-visits/{visit['id']}/messages", json={"body": "On my way"}, headers=auth_header(vol_token))

    resp = client.get("/api/messages/assignment-conversations", headers=auth_header(staff_token))
    assert resp.status_code == 200
    kinds = [(c["kind"], c["id"]) for c in resp.get_json()["conversations"]]
    assert ("home_visit", visit["id"]) in kinds


def test_assignment_conversations_is_admin_staff_only(client, make_user, auth_header):
    _, vol_token, _ = make_user(email="noassignconv@example.com")
    resp = client.get("/api/messages/assignment-conversations", headers=auth_header(vol_token))
    assert resp.status_code == 403
