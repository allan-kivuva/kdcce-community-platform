def _verify(client, make_staff_user, auth_header, user_id):
    _, admin_token = make_staff_user("admin", email="avail-admin@example.com")
    client.patch(f"/api/volunteers/{user_id}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return admin_token


def _volunteer_id(client, auth_header, admin_token, email):
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    return next(v for v in volunteers if v["email"] == email)["id"]


# ---------- Self-service availability CRUD ----------

def test_volunteer_can_add_list_and_delete_own_availability(client, make_user, auth_header):
    _, token, _ = make_user(email="avail-self@example.com")

    resp = client.post("/api/volunteers/me/availability", json={"day_of_week": "Monday", "start_time": "09:00", "end_time": "12:00"}, headers=auth_header(token))
    assert resp.status_code == 201
    slot = resp.get_json()["availability"]
    assert slot["day_of_week"] == "Monday"
    assert slot["start_time"] == "09:00"
    assert slot["end_time"] == "12:00"

    listed = client.get("/api/volunteers/me/availability", headers=auth_header(token)).get_json()["availability"]
    assert len(listed) == 1
    assert listed[0]["id"] == slot["id"]

    resp = client.delete(f"/api/volunteers/me/availability/{slot['id']}", headers=auth_header(token))
    assert resp.status_code == 204
    assert client.get("/api/volunteers/me/availability", headers=auth_header(token)).get_json()["availability"] == []


def test_volunteer_can_have_multiple_availability_windows(client, make_user, auth_header):
    _, token, _ = make_user(email="avail-multi@example.com")
    client.post("/api/volunteers/me/availability", json={"day_of_week": "Monday", "start_time": "09:00", "end_time": "12:00"}, headers=auth_header(token))
    client.post("/api/volunteers/me/availability", json={"day_of_week": "Wednesday", "start_time": "13:00", "end_time": "17:00"}, headers=auth_header(token))
    listed = client.get("/api/volunteers/me/availability", headers=auth_header(token)).get_json()["availability"]
    assert {s["day_of_week"] for s in listed} == {"Monday", "Wednesday"}


def test_availability_rejects_end_time_before_start_time(client, make_user, auth_header):
    _, token, _ = make_user(email="avail-bad-time@example.com")
    resp = client.post("/api/volunteers/me/availability", json={"day_of_week": "Monday", "start_time": "12:00", "end_time": "09:00"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_availability_rejects_invalid_day_of_week(client, make_user, auth_header):
    _, token, _ = make_user(email="avail-bad-day@example.com")
    resp = client.post("/api/volunteers/me/availability", json={"day_of_week": "Someday", "start_time": "09:00", "end_time": "12:00"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_volunteer_cannot_delete_another_volunteers_availability_slot(client, make_user, auth_header):
    _, token_a, _ = make_user(email="avail-a@example.com")
    _, token_b, _ = make_user(email="avail-b@example.com")
    slot = client.post("/api/volunteers/me/availability", json={"day_of_week": "Monday", "start_time": "09:00", "end_time": "12:00"}, headers=auth_header(token_a)).get_json()["availability"]

    resp = client.delete(f"/api/volunteers/me/availability/{slot['id']}", headers=auth_header(token_b))
    assert resp.status_code == 404  # anti-enumeration: not-yours looks like not-found

    # It must still be there for its actual owner.
    assert len(client.get("/api/volunteers/me/availability", headers=auth_header(token_a)).get_json()["availability"]) == 1


def test_staff_and_admin_have_no_volunteer_profile_so_get_404(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.get("/api/volunteers/me/availability", headers=auth_header(token))
    assert resp.status_code == 404


def test_unauthenticated_cannot_access_own_availability(client):
    assert client.get("/api/volunteers/me/availability").status_code == 401


# ---------- Self-service unavailability CRUD ----------

def test_volunteer_can_add_list_and_delete_own_unavailability(client, make_user, auth_header):
    _, token, _ = make_user(email="unavail-self@example.com")

    resp = client.post("/api/volunteers/me/unavailability", json={"start_date": "2026-12-20", "end_date": "2027-01-05", "reason": "Holiday travel"}, headers=auth_header(token))
    assert resp.status_code == 201
    entry = resp.get_json()["unavailability"]
    assert entry["reason"] == "Holiday travel"

    listed = client.get("/api/volunteers/me/unavailability", headers=auth_header(token)).get_json()["unavailability"]
    assert len(listed) == 1

    resp = client.delete(f"/api/volunteers/me/unavailability/{entry['id']}", headers=auth_header(token))
    assert resp.status_code == 204
    assert client.get("/api/volunteers/me/unavailability", headers=auth_header(token)).get_json()["unavailability"] == []


def test_unavailability_rejects_end_date_before_start_date(client, make_user, auth_header):
    _, token, _ = make_user(email="unavail-bad-range@example.com")
    resp = client.post("/api/volunteers/me/unavailability", json={"start_date": "2026-12-20", "end_date": "2026-12-01"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_unavailability_reason_is_optional(client, make_user, auth_header):
    _, token, _ = make_user(email="unavail-no-reason@example.com")
    resp = client.post("/api/volunteers/me/unavailability", json={"start_date": "2026-12-20", "end_date": "2026-12-25"}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["unavailability"]["reason"] is None


def test_volunteer_cannot_delete_another_volunteers_unavailability(client, make_user, auth_header):
    _, token_a, _ = make_user(email="unavail-a@example.com")
    _, token_b, _ = make_user(email="unavail-b@example.com")
    entry = client.post("/api/volunteers/me/unavailability", json={"start_date": "2026-12-20", "end_date": "2026-12-25"}, headers=auth_header(token_a)).get_json()["unavailability"]

    resp = client.delete(f"/api/volunteers/me/unavailability/{entry['id']}", headers=auth_header(token_b))
    assert resp.status_code == 404


# ---------- Admin/staff read access ----------

def test_admin_can_view_a_volunteers_availability_and_unavailability(client, make_user, make_staff_user, auth_header):
    user, token, _ = make_user(email="avail-viewed@example.com")
    admin_token = _verify(client, make_staff_user, auth_header, user["id"])
    volunteer_id = _volunteer_id(client, auth_header, admin_token, "avail-viewed@example.com")

    client.post("/api/volunteers/me/availability", json={"day_of_week": "Friday", "start_time": "08:00", "end_time": "10:00"}, headers=auth_header(token))
    client.post("/api/volunteers/me/unavailability", json={"start_date": "2026-06-01", "end_date": "2026-06-07"}, headers=auth_header(token))

    resp = client.get(f"/api/volunteers/{volunteer_id}/availability", headers=auth_header(admin_token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["availability"]) == 1
    assert body["availability"][0]["day_of_week"] == "Friday"
    assert len(body["unavailability"]) == 1


def test_staff_can_also_view_volunteer_availability(client, make_user, make_staff_user, auth_header):
    user, _, _ = make_user(email="avail-staffview@example.com")
    admin_token = _verify(client, make_staff_user, auth_header, user["id"])
    volunteer_id = _volunteer_id(client, auth_header, admin_token, "avail-staffview@example.com")

    _, staff_token = make_staff_user("staff", email="avail-staff-viewer@example.com")
    resp = client.get(f"/api/volunteers/{volunteer_id}/availability", headers=auth_header(staff_token))
    assert resp.status_code == 200


def test_volunteer_cannot_view_another_volunteers_availability_via_the_admin_route(client, make_user, make_staff_user, auth_header):
    user, _, _ = make_user(email="avail-target@example.com")
    admin_token = _verify(client, make_staff_user, auth_header, user["id"])
    volunteer_id = _volunteer_id(client, auth_header, admin_token, "avail-target@example.com")

    _, other_token, _ = make_user(email="avail-nosy@example.com")
    resp = client.get(f"/api/volunteers/{volunteer_id}/availability", headers=auth_header(other_token))
    assert resp.status_code == 403


def test_unknown_volunteer_id_returns_404(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/volunteers/999999/availability", headers=auth_header(token))
    assert resp.status_code == 404
