def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


# ---------- Authorization / IDOR ----------

def test_unauthenticated_cannot_list_notifications(client):
    resp = client.get("/api/notifications")
    assert resp.status_code == 401


def test_new_user_has_no_notifications(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.get("/api/notifications", headers=auth_header(access_token))
    assert resp.status_code == 200
    assert resp.get_json()["notifications"] == []


def test_cannot_view_another_users_notification_via_mark_read(client, make_user, make_staff_user, auth_header):
    """IDOR check: user B must not be able to touch user A's notification,
    and the failure must look identical to 'doesn't exist' (404), not
    reveal that it exists but belongs to someone else (403)."""
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-a@example.com")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_a["id"]}, headers=auth_header(admin_token))

    notif = client.get("/api/notifications", headers=auth_header(vol_a_token)).get_json()["notifications"][0]
    _, vol_b_token, _ = make_user(email="outsider@example.com")

    resp = client.patch(f"/api/notifications/{notif['id']}", json={"is_read": True}, headers=auth_header(vol_b_token))
    assert resp.status_code == 404  # not 403 — existence isn't confirmed either


def test_cannot_delete_another_users_notification(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-b@example.com")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_a["id"]}, headers=auth_header(admin_token))
    notif = client.get("/api/notifications", headers=auth_header(vol_a_token)).get_json()["notifications"][0]
    _, vol_b_token, _ = make_user(email="outsider2@example.com")

    resp = client.delete(f"/api/notifications/{notif['id']}", headers=auth_header(vol_b_token))
    assert resp.status_code == 404
    # And it must still exist for the real owner afterward (2: the
    # verification notification from becoming Verified, plus this one).
    still_there = client.get("/api/notifications", headers=auth_header(vol_a_token)).get_json()["notifications"]
    assert len(still_there) == 2


# ---------- Own notification CRUD ----------

def test_mark_own_notification_read_and_unread(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-c@example.com")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))
    notif = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"][0]
    assert notif["is_read"] is False

    read = client.patch(f"/api/notifications/{notif['id']}", json={"is_read": True}, headers=auth_header(vol_token))
    assert read.status_code == 200
    assert read.get_json()["notification"]["is_read"] is True
    assert read.get_json()["notification"]["read_at"] is not None

    unread = client.patch(f"/api/notifications/{notif['id']}", json={"is_read": False}, headers=auth_header(vol_token))
    assert unread.get_json()["notification"]["is_read"] is False
    assert unread.get_json()["notification"]["read_at"] is None


def test_update_rejects_missing_is_read(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.patch("/api/notifications/999", json={}, headers=auth_header(access_token))
    # Ownership check runs first (404, since it's not theirs / doesn't
    # exist) — the schema validation error would only surface for a
    # notification that actually is theirs.
    assert resp.status_code == 404


def test_delete_own_notification(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-d@example.com")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))
    notif = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"][0]

    resp = client.delete(f"/api/notifications/{notif['id']}", headers=auth_header(vol_token))
    assert resp.status_code == 204
    # The volunteer-verification notification from fixture setup remains —
    # only the deleted one is gone.
    remaining = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert len(remaining) == 1
    assert remaining[0]["notification_type"] == "Volunteer Verified"


def test_unread_count(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-e@example.com")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "y", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))

    resp = client.get("/api/notifications/unread-count", headers=auth_header(vol_token))
    # 3: volunteer-verified (from fixture setup) + home visit + assistance.
    assert resp.get_json()["unread_count"] == 3


def test_mark_all_read(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-f@example.com")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "y", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))

    resp = client.post("/api/notifications/mark-all-read", headers=auth_header(vol_token))
    assert resp.status_code == 200
    # 3: volunteer-verified (from fixture setup) + home visit + assistance.
    assert resp.get_json()["updated"] == 3
    assert client.get("/api/notifications/unread-count", headers=auth_header(vol_token)).get_json()["unread_count"] == 0


def test_list_filters_unread_only_and_type(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-g@example.com")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))
    notif = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"][0]
    client.patch(f"/api/notifications/{notif['id']}", json={"is_read": True}, headers=auth_header(vol_token))
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "y", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))

    # Unread: volunteer-verified (never marked read) + the new assistance
    # assignment — the home visit one was explicitly marked read above.
    unread = client.get("/api/notifications?unread_only=true", headers=auth_header(vol_token)).get_json()["notifications"]
    unread_types = {n["notification_type"] for n in unread}
    assert unread_types == {"Volunteer Verified", "Assistance Request Assignment"}

    by_type = client.get("/api/notifications?notification_type=Home Visit Assignment", headers=auth_header(vol_token)).get_json()["notifications"]
    assert len(by_type) == 1


def test_list_is_paginated(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-h@example.com")
    for i in range(3):
        m = _register_member(client, admin_token, auth_header, name=f"Member {i}")
        client.post("/api/home-visits", json={"elderly_member_id": m["id"], "reason": "x", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))

    resp = client.get("/api/notifications?page=1&per_page=2", headers=auth_header(vol_token))
    body = resp.get_json()
    assert len(body["notifications"]) == 2
    # 4: volunteer-verified (from fixture setup) + 3 home visits.
    assert body["pagination"]["total"] == 4
    assert body["pagination"]["pages"] == 2


# ---------- Trigger regressions: each existing endpoint's side effect ----------

def test_home_visit_creation_with_assignee_notifies_assignee(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-i@example.com")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))

    # Filter out the fixture's own "Volunteer Verified" notification —
    # this test is only about what the home-visit endpoint itself creates.
    notifications = client.get("/api/notifications?notification_type=Home Visit Assignment", headers=auth_header(vol_token)).get_json()["notifications"]
    assert len(notifications) == 1
    assert notifications[0]["related_resource_type"] == "home_visit"


def test_home_visit_reassignment_via_patch_notifies_new_assignee(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x"}, headers=auth_header(admin_token)).get_json()["visit"]
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-j@example.com")

    client.patch(f"/api/home-visits/{visit['id']}", json={"assigned_to_id": vol["id"]}, headers=auth_header(admin_token))
    notifications = client.get("/api/notifications?notification_type=Home Visit Assignment", headers=auth_header(vol_token)).get_json()["notifications"]
    assert len(notifications) == 1


def test_creating_unassigned_home_visit_notifies_nobody(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x"}, headers=auth_header(admin_token))
    assert client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"] == []


def test_assistance_request_assignment_notifies_assignee(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vera-k@example.com")
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "y", "assigned_to_id": vol["id"]}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications?notification_type=Assistance Request Assignment", headers=auth_header(vol_token)).get_json()["notifications"]
    assert len(notifications) == 1


def test_volunteer_verification_notifies_the_volunteer(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="vera-l@example.com")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "vera-l@example.com")["id"]

    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert len(notifications) == 1
    assert notifications[0]["notification_type"] == "Volunteer Verified"


def test_volunteer_rejection_does_not_send_verified_notification(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="vera-m@example.com")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "vera-m@example.com")["id"]

    client.patch(f"/api/volunteers/{vid}", json={"status": "Rejected"}, headers=auth_header(admin_token))
    assert client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"] == []


def test_low_stock_movement_notifies_admin_and_staff(client, make_staff_user, auth_header):
    admin_user, admin_token = make_staff_user("admin")
    staff_user, staff_token = make_staff_user("staff", email="caregiver-notif@example.com")
    item = client.post("/api/inventory", json={"name": "Rice", "category": "Food", "unit": "kg", "minimum_stock": 10}, headers=auth_header(admin_token)).get_json()["item"]

    # Stock-in above minimum first — must NOT notify (not crossing into low).
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 20}, headers=auth_header(admin_token))
    assert client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"] == []

    # Stock-out crossing at/below minimum — must notify every admin/staff.
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Out", "quantity": 15}, headers=auth_header(admin_token))
    admin_notifs = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"]
    staff_notifs = client.get("/api/notifications", headers=auth_header(staff_token)).get_json()["notifications"]
    assert len(admin_notifs) == 1
    assert len(staff_notifs) == 1
    assert admin_notifs[0]["notification_type"] == "Low Inventory Alert"


def test_low_stock_alert_does_not_repeat_while_already_low(client, make_staff_user, auth_header):
    """Regression: only the transition into low stock should alert — not
    every subsequent movement while it stays low, or admins get spammed."""
    _, admin_token = make_staff_user("admin")
    item = client.post("/api/inventory", json={"name": "Rice", "category": "Food", "unit": "kg", "minimum_stock": 10}, headers=auth_header(admin_token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 5}, headers=auth_header(admin_token))  # already <= minimum
    assert client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"] == []  # 5 <= 10, but this was the first movement, "was_low" started at 0<=10=True already

    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 1}, headers=auth_header(admin_token))
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Out", "quantity": 1}, headers=auth_header(admin_token))
    notifications = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"]
    assert len(notifications) == 0  # stayed low/at-minimum throughout — never transitioned from above to at/below
