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
    client.post("/api/activities", json={"title": "Morning Walk", "activity_type": "Walking", "scheduled_at": "2026-08-27T09:00:00+00:00"}, headers=auth_header(token))
    # Unscheduled visit must not appear.
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "no schedule"}, headers=auth_header(token))

    resp = client.get("/api/calendar", headers=auth_header(token))
    assert resp.status_code == 200
    events = resp.get_json()["events"]
    assert len(events) == 3
    assert [e["type"] for e in events] == ["home_visit", "assistance_request", "activity"]
    assert events[0]["scheduled_at"] < events[1]["scheduled_at"] < events[2]["scheduled_at"]


def test_activity_event_shape(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/activities", json={"title": "Morning Walk", "activity_type": "Walking", "scheduled_at": "2026-08-27T09:00:00+00:00", "facilitator_id": None}, headers=auth_header(token))
    activity_id = resp.get_json()["activity"]["id"]

    events = client.get("/api/calendar", headers=auth_header(token)).get_json()["events"]
    activity_events = [e for e in events if e["type"] == "activity"]
    assert len(activity_events) == 1
    event = activity_events[0]
    assert event["id"] == activity_id
    assert event["title"] == "Morning Walk"
    assert event["activity_type"] == "Walking"
    assert event["status"] == "Scheduled"
    assert event["elderly_member_id"] is None
    assert event["elderly_member_name"] is None
    assert event["assigned_to_id"] is None
    assert event["assigned_to"] is None


def test_activity_with_facilitator_uses_assigned_to_fields(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    vol, _ = _verified_volunteer(client, make_user, auth_header, token, email="cal-facilitator@example.com")
    client.post("/api/activities", json={"title": "Games Night", "activity_type": "Games", "scheduled_at": "2026-08-27T09:00:00+00:00", "facilitator_id": vol["id"]}, headers=auth_header(token))

    events = client.get("/api/calendar", headers=auth_header(token)).get_json()["events"]
    event = next(e for e in events if e["type"] == "activity")
    assert event["assigned_to_id"] == vol["id"]
    assert event["assigned_to"] == vol["name"]


def test_volunteer_sees_only_their_own_events(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, token, email="cal-c@example.com")
    vol_b, _ = _verified_volunteer(client, make_user, auth_header, token, email="cal-d@example.com")

    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "for A", "assigned_to_id": vol_a["id"], "scheduled_at": "2026-08-25T10:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "for B", "assigned_to_id": vol_b["id"], "scheduled_at": "2026-08-26T10:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/activities", json={"title": "A's activity", "activity_type": "Social", "scheduled_at": "2026-08-25T09:00:00+00:00", "facilitator_id": vol_a["id"]}, headers=auth_header(token))
    client.post("/api/activities", json={"title": "B's activity", "activity_type": "Social", "scheduled_at": "2026-08-26T09:00:00+00:00", "facilitator_id": vol_b["id"]}, headers=auth_header(token))

    events = client.get("/api/calendar", headers=auth_header(vol_a_token)).get_json()["events"]
    assert len(events) == 2
    assert all(e["assigned_to_id"] == vol_a["id"] for e in events)
    assert {e["type"] for e in events} == {"home_visit", "activity"}


def test_date_range_filter(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "scheduled_at": "2026-01-01T10:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "scheduled_at": "2026-08-25T10:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/activities", json={"title": "Out of range", "activity_type": "Social", "scheduled_at": "2026-01-05T09:00:00+00:00"}, headers=auth_header(token))
    client.post("/api/activities", json={"title": "In range", "activity_type": "Social", "scheduled_at": "2026-08-20T09:00:00+00:00"}, headers=auth_header(token))

    events = client.get("/api/calendar?start=2026-08-01&end=2026-08-31", headers=auth_header(token)).get_json()["events"]
    assert len(events) == 2
    assert {e["type"] for e in events} == {"home_visit", "activity"}


def test_unauthenticated_cannot_access_calendar(client):
    assert client.get("/api/calendar").status_code == 401


def test_recurring_series_generated_visits_carry_their_series_id_on_the_calendar(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)

    resp = client.post(
        "/api/recurring-visits",
        json={"elderly_member_id": member["id"], "reason": "Weekly check", "frequency": "weekly", "start_date": "2026-08-03", "scheduled_time": "09:00", "occurrence_count": 2},
        headers=auth_header(token),
    )
    series_id = resp.get_json()["series"]["id"]

    events = client.get("/api/calendar", headers=auth_header(token)).get_json()["events"]
    recurring_events = [e for e in events if e["type"] == "home_visit" and e.get("recurring_series_id") == series_id]
    assert len(recurring_events) == 2


def test_one_off_visit_has_null_recurring_series_id_on_the_calendar(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "scheduled_at": "2026-08-25T10:00:00+00:00"}, headers=auth_header(token))

    events = client.get("/api/calendar", headers=auth_header(token)).get_json()["events"]
    visit_event = next(e for e in events if e["type"] == "home_visit")
    assert visit_event["recurring_series_id"] is None
