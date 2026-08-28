def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


VALID_ACTIVITY = {"title": "Morning Walk", "activity_type": "Walking", "scheduled_at": "2026-01-15T09:00:00+00:00"}


def test_staff_can_create_activity(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["activity"]
    assert body["status"] == "Scheduled"
    assert body["participant_count"] == 0


def test_volunteer_cannot_create_activity(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_create_rejects_invalid_type(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/activities", json={**VALID_ACTIVITY, "activity_type": "Karaoke"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_create_rejects_missing_scheduled_at(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    payload = {k: v for k, v in VALID_ACTIVITY.items() if k != "scheduled_at"}
    resp = client.post("/api/activities", json=payload, headers=auth_header(token))
    assert resp.status_code == 400


def test_cannot_set_unverified_volunteer_as_facilitator(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    volunteer_user, _, _ = make_user(email="unverified@example.com")
    resp = client.post("/api/activities", json={**VALID_ACTIVITY, "facilitator_id": volunteer_user["id"]}, headers=auth_header(token))
    assert resp.status_code == 400


def test_can_set_verified_volunteer_as_facilitator(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    volunteer_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    resp = client.post("/api/activities", json={**VALID_ACTIVITY, "facilitator_id": volunteer_user["id"]}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["activity"]["facilitator"] == "Vera Volunteer"


def test_can_set_staff_as_facilitator(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    staff_user, _ = make_staff_user("staff", email="facilitator@example.com")
    resp = client.post("/api/activities", json={**VALID_ACTIVITY, "facilitator_id": staff_user["id"]}, headers=auth_header(admin_token))
    assert resp.status_code == 201


def test_list_filters_by_date_type_and_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/activities", json={"title": "A", "activity_type": "Walking", "scheduled_at": "2026-01-15T09:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/activities", json={"title": "B", "activity_type": "Games", "scheduled_at": "2026-01-16T09:00:00+00:00"}, headers=auth_header(token))

    by_date = client.get("/api/activities?date=2026-01-15", headers=auth_header(token))
    assert len(by_date.get_json()["activities"]) == 1

    by_type = client.get("/api/activities?activity_type=Games", headers=auth_header(token))
    assert len(by_type.get_json()["activities"]) == 1
    assert by_type.get_json()["activities"][0]["title"] == "B"


def test_list_rejects_bad_date_format(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/activities?date=not-a-date", headers=auth_header(token))
    assert resp.status_code == 400


def test_status_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    client.patch(f"/api/activities/{activity['id']}", json={"status": "In Progress"}, headers=auth_header(token))

    patched = client.patch(f"/api/activities/{activity['id']}", json={"location": "Community Hall"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["activity"]["status"] == "In Progress"
    assert patched.get_json()["activity"]["location"] == "Community Hall"


# ---------- Participants ----------

def test_staff_can_register_a_participant(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]

    resp = client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["participant"]
    assert body["status"] == "Registered"
    assert body["elderly_member_name"] == "Mary Achieng"

    updated = client.get(f"/api/activities/{activity['id']}", headers=auth_header(token))
    assert updated.get_json()["activity"]["participant_count"] == 1


def test_cannot_register_same_member_twice(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    resp = client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 409


def test_mark_attendance_updates_participant_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    participant = client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["participant"]

    resp = client.patch(f"/api/activities/{activity['id']}/participants/{participant['id']}", json={"status": "Attended"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["participant"]["status"] == "Attended"


def test_participant_update_rejects_invalid_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    participant = client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["participant"]

    resp = client.patch(f"/api/activities/{activity['id']}/participants/{participant['id']}", json={"status": "Excited"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_volunteer_cannot_register_participant(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(admin_token)).get_json()["activity"]
    _, access_token, _ = make_user()

    resp = client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_registration_rejects_unknown_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    resp = client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_registration_rejects_unknown_activity(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/activities/999/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 404


def test_list_participants_for_an_activity(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _register_member(client, token, auth_header, "Mary Achieng")
    m2 = _register_member(client, token, auth_header, "John Otieno")
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": m1["id"]}, headers=auth_header(token))
    client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": m2["id"]}, headers=auth_header(token))

    resp = client.get(f"/api/activities/{activity['id']}/participants", headers=auth_header(token))
    assert len(resp.get_json()["participants"]) == 2


# ---------- Delete ----------

def test_admin_can_delete_activity_with_no_participants(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    resp = client.delete(f"/api/activities/{activity['id']}", headers=auth_header(token))
    assert resp.status_code == 204


def test_cannot_delete_activity_with_participants(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    resp = client.delete(f"/api/activities/{activity['id']}", headers=auth_header(token))
    assert resp.status_code == 409


def test_staff_cannot_delete_activity(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    activity = client.post("/api/activities", json=VALID_ACTIVITY, headers=auth_header(token)).get_json()["activity"]
    resp = client.delete(f"/api/activities/{activity['id']}", headers=auth_header(token))
    assert resp.status_code == 403
