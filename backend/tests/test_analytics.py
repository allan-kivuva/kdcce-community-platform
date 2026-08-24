import datetime


def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


# ---------- Authorization ----------

def test_unauthenticated_cannot_access_dashboard(client):
    resp = client.get("/api/analytics/dashboard")
    assert resp.status_code == 401


def test_volunteer_cannot_access_dashboard(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.get("/api/analytics/dashboard", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_staff_can_access_dashboard(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    assert resp.status_code == 200


# ---------- Shape / empty dataset safety ----------

def test_dashboard_sections_present_on_empty_dataset(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]
    for section in ("elderly_care", "home_community", "health", "feeding_resources", "activities", "incidents", "follow_ups", "upcoming_visits", "volunteer_performance", "today_activity"):
        assert section in body
    assert body["follow_ups"]["pending"] == 0
    assert body["upcoming_visits"]["count"] == 0
    assert body["volunteer_performance"]["active_volunteers"] == 0
    assert body["volunteer_performance"]["completion_rate"] == 0.0
    assert body["elderly_care"]["total_elderly_members"] == 0
    assert body["health"]["clinic_visits"] is None


def test_trend_series_are_zero_filled_and_ordered(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    trend = resp.get_json()["dashboard"]["elderly_care"]["attendance_trend_7d"]
    assert len(trend) == 7
    dates = [d["date"] for d in trend]
    assert dates == sorted(dates)
    assert all(d["count"] == 0 for d in trend)
    # The last entry must be today, not some other day — proves the window
    # is anchored correctly, not just "any 7 consecutive dates."
    assert trend[-1]["date"] == datetime.date.today().isoformat()


def test_donations_trend_series_does_not_crash(client, make_staff_user, auth_header):
    """Regression: db.func.date() returns a plain string from SQLite, not
    a date object — a naive .isoformat() call on the grouped key crashes.
    This is the one trend series built from a func.date() expression
    rather than a native Date column."""
    _, token = make_staff_user("admin")
    client.post("/api/donations", json={"donor_name": "Amina", "donor_email": "amina@example.com", "amount": 500, "frequency": "one-time"})

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    assert resp.status_code == 200
    trend = resp.get_json()["dashboard"]["feeding_resources"]["donations_trend_14d"]
    assert len(trend) == 14
    today_entry = next(d for d in trend if d["date"] == datetime.date.today().isoformat())
    assert today_entry["count"] == 1


# ---------- Correctness ----------

def test_elderly_care_section_counts(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    client.post("/api/health-records", json={"elderly_member_id": member["id"], "follow_up_required": True}, headers=auth_header(token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]["elderly_care"]
    assert body["total_elderly_members"] == 1
    assert body["new_registrations_30d"] == 1
    assert body["today_attendance"] == 1
    assert body["follow_ups_required"] == 1


def test_home_community_section_counts(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, _, _ = make_user(email="vera8@example.com", name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "vera8@example.com")["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))

    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x"}, headers=auth_header(admin_token))
    r = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "y"}, headers=auth_header(admin_token)).get_json()["request"]
    client.patch(f"/api/assistance-requests/{r['id']}", json={"status": "Completed"}, headers=auth_header(admin_token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(admin_token))
    body = resp.get_json()["dashboard"]["home_community"]
    assert body["home_visits_pending"] == 1
    assert body["assistance_completed"] == 1
    assert body["active_volunteers"] == 1


def test_feeding_resources_low_stock_uses_database_comparison(client, make_staff_user, auth_header):
    """Regression: low-stock counting must not load every item into
    Python — verified indirectly here by checking correctness; the N+1
    risk itself is a code-review concern, not something a single test can
    directly measure, so this asserts the *result* is right."""
    _, token = make_staff_user("admin")
    client.post("/api/inventory", json={"name": "Rice", "category": "Food", "unit": "kg", "minimum_stock": 10}, headers=auth_header(token))
    ok_item = client.post("/api/inventory", json={"name": "Beans", "category": "Food", "unit": "kg", "minimum_stock": 5}, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{ok_item['id']}/movements", json={"movement_type": "In", "quantity": 50}, headers=auth_header(token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    assert resp.get_json()["dashboard"]["feeding_resources"]["low_stock_items"] == 1


def test_feeding_resources_meals_and_donations(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    client.post("/api/donations", json={"donor_name": "Amina", "donor_email": "amina@example.com", "amount": 500, "frequency": "one-time"})

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]["feeding_resources"]
    assert body["meals_served_7d"] == 1
    assert body["donations_30d"] == 1


def test_activities_section_upcoming_and_attended(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)).isoformat()
    activity = client.post("/api/activities", json={"title": "Walk", "activity_type": "Walking", "scheduled_at": future}, headers=auth_header(token)).get_json()["activity"]
    participant = client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["participant"]
    client.patch(f"/api/activities/{activity['id']}/participants/{participant['id']}", json={"status": "Attended"}, headers=auth_header(token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]["activities"]
    assert body["upcoming_count"] == 1
    assert body["upcoming"][0]["title"] == "Walk"
    assert body["attended_30d"] == 1


def test_incidents_section_counts_and_recent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/incidents", json={"elderly_member_id": member["id"], "incident_type": "Fall", "description": "x", "follow_up_required": True}, headers=auth_header(token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]["incidents"]
    assert body["open"] == 1
    assert body["follow_up_required"] == 1
    assert len(body["recent"]) == 1
    assert body["recent"][0]["elderly_member_name"] == "Mary Achieng"
    # A dashboard tile must not leak the sensitive free-text description —
    # only type/status/date/who, same fields already visible elsewhere.
    assert "description" not in body["recent"][0]


def test_follow_ups_section_counts_pending_and_overdue(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "Overdue", "due_date": "2020-01-01"}, headers=auth_header(token))
    client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "Not due yet", "due_date": "2099-01-01"}, headers=auth_header(token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]["follow_ups"]
    assert body["pending"] == 2
    assert body["overdue"] == 1


def test_upcoming_visits_section(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "scheduled_at": "2099-01-01T10:00:00+00:00"}, headers=auth_header(token))
    # Past-scheduled and unscheduled visits must not count as "upcoming".
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x"}, headers=auth_header(token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]["upcoming_visits"]
    assert body["count"] == 1
    assert body["upcoming"][0]["elderly_member_name"] == "Mary Achieng"


def test_volunteer_performance_section_reflects_real_data(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_user, _, _ = make_user(email="perf@example.com")
    volunteers = client.get("/api/volunteers", headers=auth_header(token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "perf@example.com")["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(token))

    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(token)).get_json()["visit"]
    client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed"}, headers=auth_header(token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]["volunteer_performance"]
    assert body["active_volunteers"] == 1
    assert body["total_assignments"] == 1
    assert body["completed_assignments"] == 1
    assert body["completion_rate"] == 100.0


def test_today_activity_shows_only_todays_events(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    resp = client.get("/api/analytics/dashboard", headers=auth_header(token))
    body = resp.get_json()["dashboard"]["today_activity"]
    assert len(body["attendance"]) == 1
    assert body["attendance"][0]["elderly_member_name"] == "Mary Achieng"
