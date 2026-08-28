def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def test_admin_sees_all_scheduled_events(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_a, _ = _verified_volunteer(client, make_user, auth_header, token, email="cal-a@example.com")
    vol_b, _ = _verified_volunteer(client, make_user, auth_header, token, email="cal-b@example.com")

    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_a["id"], "scheduled_at": "2026-08-25T10:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "x", "assigned_to_id": vol_b["id"], "scheduled_at": "2026-08-26T10:00:00+00:00"}, headers=auth_header(token))
    # Unscheduled visit must not appear.
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "no schedule"}, headers=auth_header(token))

    resp = client.get("/api/calendar", headers=auth_header(token))
    assert resp.status_code == 200
    events = resp.get_json()["events"]
    assert len(events) == 2
    assert events[0]["scheduled_at"] < events[1]["scheduled_at"]


def test_volunteer_sees_only_their_own_events(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, token, email="cal-c@example.com")
    vol_b, _ = _verified_volunteer(client, make_user, auth_header, token, email="cal-d@example.com")

    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "for A", "assigned_to_id": vol_a["id"], "scheduled_at": "2026-08-25T10:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "for B", "assigned_to_id": vol_b["id"], "scheduled_at": "2026-08-26T10:00:00+00:00"}, headers=auth_header(token))

    events = client.get("/api/calendar", headers=auth_header(vol_a_token)).get_json()["events"]
    assert len(events) == 1
    assert events[0]["assigned_to_id"] == vol_a["id"]


def test_date_range_filter(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "scheduled_at": "2026-01-01T10:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "scheduled_at": "2026-08-25T10:00:00+00:00"}, headers=auth_header(token))

    events = client.get("/api/calendar?start=2026-08-01&end=2026-08-31", headers=auth_header(token)).get_json()["events"]
    assert len(events) == 1


def test_unauthenticated_cannot_access_calendar(client):
    assert client.get("/api/calendar").status_code == 401
