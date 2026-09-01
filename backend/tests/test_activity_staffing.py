def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com", name="Vera Volunteer"):
    user, access_token, _ = make_user(email=email, name=name)
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _create_activity(client, token, auth_header, **overrides):
    payload = {"title": "Health Fair", "activity_type": "Community Event", "scheduled_at": "2027-04-15T09:00:00+00:00", **overrides}
    return client.post("/api/activities", json=payload, headers=auth_header(token)).get_json()["activity"]


# ---------- Assignment ----------

def test_staff_can_assign_volunteer_to_a_role(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, _ = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"], "role": "Registration"}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    body = resp.get_json()["assignment"]
    assert body["role"] == "Registration"
    assert body["status"] == "Assigned"
    assert body["is_self_rsvp"] is False
    assert body["assigned_by"] == "Staffer"


def test_assigning_notifies_the_volunteer(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"], "role": "Logistics"}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Event Assigned" for n in notifications)


def test_volunteer_cannot_assign_themselves_via_staffing_endpoint(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    resp = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_cannot_assign_a_non_volunteer(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    other_staff, _ = make_staff_user("staff", email="colleague@example.com")
    activity = _create_activity(client, admin_token, auth_header)
    resp = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": other_staff["id"]}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_staff_assignment_bypasses_capacity(client, make_user, make_staff_user, auth_header):
    """Capacity governs self-RSVP; a staffing assignment for a specific
    role (e.g. one more Logistics helper) is a staff judgment call, not
    an attendee slot — deliberately not capped by the same limit."""
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, capacity=1)
    vol1, tok1 = _verified_volunteer(client, make_user, auth_header, admin_token, email="fillsslot@example.com")
    vol2, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="staffedanyway@example.com")

    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))
    resp = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol2["id"], "role": "Logistics"}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["assignment"]["status"] == "Assigned"


def test_duplicate_active_assignment_rejected(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token))
    resp = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token))
    assert resp.status_code == 409


# ---------- Confirm / decline ----------

def test_volunteer_can_confirm_own_assignment(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"status": "Confirmed"}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["assignment"]["status"] == "Confirmed"
    assert resp.get_json()["assignment"]["confirmed_at"] is not None


def test_volunteer_can_decline_own_assignment(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"status": "Declined"}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["assignment"]["status"] == "Declined"


def test_volunteer_cannot_confirm_someone_elses_assignment(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="target@example.com")
    _, other_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="nosy@example.com")
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"status": "Confirmed"}, headers=auth_header(other_token))
    assert resp.status_code == 403


def test_volunteer_cannot_set_arbitrary_status_on_own_assignment(client, make_user, make_staff_user, auth_header):
    """A volunteer may confirm/decline — not mark themselves Attended,
    that's an outcome staff records."""
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"status": "Attended"}, headers=auth_header(vol_token))
    assert resp.status_code == 400


def test_volunteer_cannot_change_own_role(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"], "role": "Support"}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"role": "Facilitator"}, headers=auth_header(vol_token))
    assert resp.status_code == 400


# ---------- Attendance / check-in ----------

def test_staff_can_mark_attendance(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"status": "Attended"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["assignment"]["status"] == "Attended"


def test_staff_can_mark_no_show(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"status": "No Show"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["assignment"]["status"] == "No Show"


def test_staff_can_check_in_and_check_out(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"checked_in": True}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["assignment"]["checked_in_at"] is not None
    assert resp.get_json()["assignment"]["checked_out_at"] is None

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"checked_out": True}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["assignment"]["checked_out_at"] is not None


def test_volunteer_cannot_check_themselves_in(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    assignment = client.post(f"/api/activities/{activity['id']}/volunteers", json={"volunteer_id": vol["id"]}, headers=auth_header(admin_token)).get_json()["assignment"]

    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/{assignment['id']}", json={"checked_in": True}, headers=auth_header(vol_token))
    assert resp.status_code == 400  # not a recognized field on the self-response schema


# ---------- Read access ----------

def test_volunteer_cannot_list_all_activity_volunteers(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    _, vol_token, _ = make_user(email="noroster@example.com")
    resp = client.get(f"/api/activities/{activity['id']}/volunteers", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_volunteer_cannot_view_waitlist_directly(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    _, vol_token, _ = make_user(email="nowaitlistpeek@example.com")
    resp = client.get(f"/api/activities/{activity['id']}/waitlist", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_unknown_assignment_returns_404(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    resp = client.patch(f"/api/activities/{activity['id']}/volunteers/999999", json={"status": "Confirmed"}, headers=auth_header(admin_token))
    assert resp.status_code == 404
