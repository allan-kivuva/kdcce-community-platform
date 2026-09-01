def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


VALID = {"audience_type": "All", "title": "Reminder", "message": "Please check your assignments for this week."}


def test_admin_can_send_broadcast(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    make_user(email="broadcasttarget@example.com")
    resp = client.post("/api/broadcasts", json=VALID, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["broadcast"]["recipient_count"] >= 1


def test_staff_can_send_broadcast(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/broadcasts", json=VALID, headers=auth_header(token))
    assert resp.status_code == 201


def test_volunteer_cannot_send_broadcast(client, make_user, auth_header):
    _, token, _ = make_user(email="nobroadcast@example.com")
    resp = client.post("/api/broadcasts", json=VALID, headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_send_broadcast(client):
    resp = client.post("/api/broadcasts", json=VALID)
    assert resp.status_code == 401


def test_broadcast_notifies_all_volunteers(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="broadcastrecipient@example.com")

    client.post("/api/broadcasts", json={**VALID, "audience_type": "Volunteers"}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Broadcast Message" for n in notifications)


def test_broadcast_sender_is_not_notified_of_own_broadcast(client, make_staff_user, auth_header):
    admin, admin_token = make_staff_user("admin")
    client.post("/api/broadcasts", json={**VALID, "audience_type": "Admin"}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"]
    assert all(n["notification_type"] != "Broadcast Message" for n in notifications)


def test_selected_audience_requires_user_ids(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/broadcasts", json={**VALID, "audience_type": "Selected"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_selected_audience_only_notifies_chosen_volunteers(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    chosen, chosen_token, _ = make_user(email="broadcastchosen@example.com")
    _, other_token, _ = make_user(email="broadcastnotchosen@example.com")

    client.post("/api/broadcasts", json={**VALID, "audience_type": "Selected", "selected_user_ids": [chosen["id"]]}, headers=auth_header(admin_token))

    chosen_notifications = client.get("/api/notifications", headers=auth_header(chosen_token)).get_json()["notifications"]
    other_notifications = client.get("/api/notifications", headers=auth_header(other_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Broadcast Message" for n in chosen_notifications)
    assert all(n["notification_type"] != "Broadcast Message" for n in other_notifications)


def test_verified_volunteers_audience_excludes_pending(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, pending_token, _ = make_user(email="pendingbroadcast@example.com")
    _, verified_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="verifiedbroadcast@example.com")

    client.post("/api/broadcasts", json={**VALID, "audience_type": "Verified Volunteers"}, headers=auth_header(admin_token))

    pending_notifications = client.get("/api/notifications", headers=auth_header(pending_token)).get_json()["notifications"]
    verified_notifications = client.get("/api/notifications", headers=auth_header(verified_token)).get_json()["notifications"]
    assert all(n["notification_type"] != "Broadcast Message" for n in pending_notifications)
    assert any(n["notification_type"] == "Broadcast Message" for n in verified_notifications)


def test_retry_with_same_client_token_does_not_duplicate_notifications(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="idempotent@example.com")

    payload = {**VALID, "audience_type": "Volunteers", "client_token": "fixed-token-123"}
    r1 = client.post("/api/broadcasts", json=payload, headers=auth_header(admin_token))
    r2 = client.post("/api/broadcasts", json=payload, headers=auth_header(admin_token))

    assert r1.status_code == 201
    assert r2.status_code == 200  # not created again
    assert r1.get_json()["broadcast"]["id"] == r2.get_json()["broadcast"]["id"]

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    broadcast_notifications = [n for n in notifications if n["notification_type"] == "Broadcast Message"]
    assert len(broadcast_notifications) == 1


def test_admin_can_list_broadcast_history(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    client.post("/api/broadcasts", json=VALID, headers=auth_header(admin_token))

    resp = client.get("/api/broadcasts", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert len(resp.get_json()["broadcasts"]) >= 1


def test_volunteer_cannot_list_broadcast_history(client, make_user, auth_header):
    _, token, _ = make_user(email="nobroadcasthistory@example.com")
    resp = client.get("/api/broadcasts", headers=auth_header(token))
    assert resp.status_code == 403
