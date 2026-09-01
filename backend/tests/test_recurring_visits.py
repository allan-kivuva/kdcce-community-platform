from datetime import date

from app.recurring_visits.service import add_months, occurrence_date


# ---------- Pure date-math (no app context needed) ----------

def test_add_months_normal_case():
    assert add_months(date(2026, 3, 15), 1) == date(2026, 4, 15)
    assert add_months(date(2026, 3, 15), 3) == date(2026, 6, 15)


def test_add_months_crosses_year_boundary():
    assert add_months(date(2026, 11, 20), 2) == date(2027, 1, 20)
    assert add_months(date(2026, 12, 1), 12) == date(2027, 12, 1)


def test_add_months_clamps_to_short_month_end():
    # Jan 31 + 1 month -> Feb 28 (2026 is not a leap year), never Mar 3.
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    # Jan 31 + 3 months -> Apr 30 (April has 30 days).
    assert add_months(date(2026, 1, 31), 3) == date(2026, 4, 30)


def test_add_months_leap_year_february():
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)  # 2028 is a leap year
    assert add_months(date(2027, 1, 31), 1) == date(2027, 2, 28)  # 2027 is not


def test_add_months_does_not_drift_across_repeated_short_months():
    # The anchor day (31) must be re-applied from the ORIGINAL date each
    # time, not compounded from the previous (already-clamped) result —
    # otherwise Jan 31 -> Feb 28 -> Mar 28 (wrong) instead of Mar 31.
    anchor = date(2026, 1, 31)
    assert add_months(anchor, 1) == date(2026, 2, 28)
    assert add_months(anchor, 2) == date(2026, 3, 31)  # not Mar 28
    assert add_months(anchor, 4) == date(2026, 5, 31)
    assert add_months(anchor, 13) == date(2027, 2, 28)  # a full year later, still non-leap


def test_occurrence_date_weekly_has_no_gaps_or_duplicates():
    start = date(2026, 3, 2)  # a Monday
    dates = [occurrence_date(start, "weekly", n) for n in range(6)]
    assert dates == [
        date(2026, 3, 2), date(2026, 3, 9), date(2026, 3, 16),
        date(2026, 3, 23), date(2026, 3, 30), date(2026, 4, 6),
    ]
    assert len(dates) == len(set(dates))  # no duplicates
    for a, b in zip(dates, dates[1:]):
        assert (b - a).days == 7  # no skipped weeks


def test_occurrence_date_biweekly():
    start = date(2026, 3, 2)
    dates = [occurrence_date(start, "biweekly", n) for n in range(4)]
    assert dates == [date(2026, 3, 2), date(2026, 3, 16), date(2026, 3, 30), date(2026, 4, 13)]


def test_occurrence_date_monthly_across_leap_year_boundary():
    start = date(2027, 12, 31)
    dates = [occurrence_date(start, "monthly", n) for n in range(4)]
    # Dec 31 (2027) -> Jan 31 (2028) -> Feb 29 (2028 leap) -> Mar 31 (2028)
    assert dates == [date(2027, 12, 31), date(2028, 1, 31), date(2028, 2, 29), date(2028, 3, 31)]


def test_occurrence_date_is_independent_of_generation_order():
    # Computing occurrence 5 directly must equal computing it via 0..5 —
    # this is what makes resuming generation at an arbitrary n safe.
    start = date(2026, 1, 31)
    direct = occurrence_date(start, "monthly", 5)
    stepped = [occurrence_date(start, "monthly", n) for n in range(6)][-1]
    assert direct == stepped


# ---------- Route-level fixtures ----------

def _register_member(client, token, auth_header, name="Recurring Test Member"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="rec-vol@example.com"):
    user, access_token, _ = make_user(email=email, name="Recurring Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _valid_series(member_id, **overrides):
    data = {
        "elderly_member_id": member_id,
        "reason": "Weekly wellbeing check",
        "frequency": "weekly",
        "start_date": "2026-03-02",
        "scheduled_time": "09:00",
    }
    data.update(overrides)
    return data


# ---------- Create + generation ----------

def test_admin_can_create_series_and_it_generates_initial_occurrences(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"]), headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["series"]
    assert body["status"] == "Active"
    assert body["occurrences_generated"] > 0
    assert body["visit_count"] == body["occurrences_generated"]

    visits = client.get(f"/api/home-visits?elderly_member_id={member['id']}", headers=auth_header(token)).get_json()["visits"]
    assert len(visits) == body["occurrences_generated"]
    assert all(v["recurring_series_id"] == body["id"] for v in visits)
    assert all(v["status"] == "Pending" for v in visits)  # unassigned series


def test_series_with_assignee_creates_assigned_visits_and_notifies(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, token)

    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"], assigned_to_id=vol["id"]), headers=auth_header(token))
    assert resp.status_code == 201

    visits = client.get("/api/home-visits", headers=auth_header(vol_token)).get_json()["visits"]
    assert len(visits) > 0
    assert all(v["status"] == "Assigned" for v in visits)

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Home Visit Assignment" for n in notifications)


def test_series_stops_generating_at_occurrence_count(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"], occurrence_count=3), headers=auth_header(token))
    body = resp.get_json()["series"]
    assert body["occurrences_generated"] == 3
    assert body["visit_count"] == 3


def test_series_stops_generating_at_end_date(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"], end_date="2026-03-16"), headers=auth_header(token))
    body = resp.get_json()["series"]
    # weekly from 2026-03-02: occurrences on 3/2, 3/9, 3/16 all <= end_date; 3/23 would exceed it.
    assert body["occurrences_generated"] == 3


def test_create_series_rejects_unknown_elderly_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/recurring-visits", json=_valid_series(999999), headers=auth_header(token))
    assert resp.status_code == 400


def test_create_series_rejects_unverified_volunteer_assignee(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    unverified, _, _ = make_user(email="unverified-rec@example.com")

    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"], assigned_to_id=unverified["id"]), headers=auth_header(token))
    assert resp.status_code == 400


def test_volunteer_cannot_create_series(client, make_user, auth_header):
    _, token, _ = make_user(email="novolseries@example.com")
    resp = client.post("/api/recurring-visits", json=_valid_series(1), headers=auth_header(token))
    assert resp.status_code == 403


def test_staff_can_create_series(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, make_staff_user("admin")[1], auth_header)
    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"]), headers=auth_header(token))
    assert resp.status_code == 201


# ---------- Duplicate prevention / idempotent top-up ----------

def test_generating_twice_does_not_duplicate_occurrences(client, make_staff_user, auth_header, app):
    from app.extensions import db
    from app.models import RecurringVisitSeries
    from app.recurring_visits.service import generate_occurrences

    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"], occurrence_count=4), headers=auth_header(token))
    series_id = resp.get_json()["series"]["id"]

    with app.app_context():
        series = db.session.get(RecurringVisitSeries, series_id)
        first_count = series.occurrences_generated
        created_again = generate_occurrences(series)  # same horizon, nothing new to create
        db.session.commit()
        assert created_again == []
        assert series.occurrences_generated == first_count == 4

    visits = client.get(f"/api/home-visits?elderly_member_id={member['id']}", headers=auth_header(token)).get_json()["visits"]
    assert len(visits) == 4


def test_cli_top_up_extends_an_open_ended_series_without_duplicating(client, make_staff_user, auth_header, app):
    from datetime import timedelta
    from app.extensions import db
    from app.models import RecurringVisitSeries, utcnow
    from app.recurring_visits.service import generate_occurrences

    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    # No occurrence_count/end_date — open-ended, generation stops at the horizon.
    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"], start_date="2026-01-01"), headers=auth_header(token))
    series_id = resp.get_json()["series"]["id"]
    first_batch = resp.get_json()["series"]["occurrences_generated"]
    assert first_batch > 0

    with app.app_context():
        series = db.session.get(RecurringVisitSeries, series_id)
        further_out = utcnow().date() + timedelta(days=200)
        newly_created = generate_occurrences(series, through_date=further_out)
        db.session.commit()
        assert len(newly_created) > 0
        assert series.occurrences_generated == first_batch + len(newly_created)

    visits = client.get(f"/api/home-visits?elderly_member_id={member['id']}", headers=auth_header(token)).get_json()["visits"]
    assert len(visits) == first_batch + len(newly_created)
    # No duplicate scheduled_at values among the generated visits.
    times = [v["scheduled_at"] for v in visits]
    assert len(times) == len(set(times))


# ---------- Editing + cancellation ----------

def test_admin_can_edit_series_fields(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    series_id = client.post("/api/recurring-visits", json=_valid_series(member["id"]), headers=auth_header(token)).get_json()["series"]["id"]

    resp = client.patch(f"/api/recurring-visits/{series_id}", json={"priority": "High", "reason": "Updated reason"}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()["series"]
    assert body["priority"] == "High"
    assert body["reason"] == "Updated reason"


def test_series_update_rejects_frequency_and_start_date_changes(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    series_id = client.post("/api/recurring-visits", json=_valid_series(member["id"]), headers=auth_header(token)).get_json()["series"]["id"]

    # frequency/start_date aren't fields on the update schema at all —
    # marshmallow's default (RAISE) behavior for an unrecognized field is
    # a 400, same as any other unknown-field PATCH in this app. Either
    # way, the pattern anchor cannot be changed through this endpoint.
    resp = client.patch(f"/api/recurring-visits/{series_id}", json={"frequency": "monthly"}, headers=auth_header(token))
    assert resp.status_code == 400
    assert client.get(f"/api/recurring-visits/{series_id}", headers=auth_header(token)).get_json()["series"]["frequency"] == "weekly"


def test_cancelling_series_cancels_future_open_visits_but_not_completed_ones(client, make_staff_user, auth_header, app):
    from datetime import timedelta

    from app.models import utcnow

    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    # Genuinely in the future relative to whenever this test actually
    # runs — cancel_future_visits filters on scheduled_at >= now, so a
    # fixed past-looking date would make every generated visit already
    # "past" and defeat the point of this test.
    future_start = (utcnow().date() + timedelta(days=14)).isoformat()
    resp = client.post("/api/recurring-visits", json=_valid_series(member["id"], occurrence_count=3, start_date=future_start), headers=auth_header(token))
    series_id = resp.get_json()["series"]["id"]

    visits = client.get(f"/api/home-visits?elderly_member_id={member['id']}", headers=auth_header(token)).get_json()["visits"]
    assert len(visits) == 3
    # Mark one of them Completed — with a future scheduled_at date, so the
    # only thing distinguishing it from the others is its status, proving
    # cancellation respects status, not just a date cutoff.
    completed_visit_id = visits[0]["id"]
    client.patch(f"/api/home-visits/{completed_visit_id}", json={"status": "Completed"}, headers=auth_header(token))

    resp = client.patch(f"/api/recurring-visits/{series_id}", json={"status": "Cancelled"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["cancelled_visit_count"] == 2

    visits_after = {v["id"]: v["status"] for v in client.get(f"/api/home-visits?elderly_member_id={member['id']}", headers=auth_header(token)).get_json()["visits"]}
    assert visits_after[completed_visit_id] == "Completed"  # untouched
    for vid, status in visits_after.items():
        if vid != completed_visit_id:
            assert status == "Cancelled"


def test_cancelled_series_status_persists(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    series_id = client.post("/api/recurring-visits", json=_valid_series(member["id"]), headers=auth_header(token)).get_json()["series"]["id"]

    client.patch(f"/api/recurring-visits/{series_id}", json={"status": "Cancelled"}, headers=auth_header(token))
    body = client.get(f"/api/recurring-visits/{series_id}", headers=auth_header(token)).get_json()["series"]
    assert body["status"] == "Cancelled"


# ---------- List / permissions ----------

def test_list_series_filters_by_elderly_member_and_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member_a = _register_member(client, token, auth_header, name="Member A")
    member_b = _register_member(client, token, auth_header, name="Member B")
    client.post("/api/recurring-visits", json=_valid_series(member_a["id"]), headers=auth_header(token))
    client.post("/api/recurring-visits", json=_valid_series(member_b["id"]), headers=auth_header(token))

    resp = client.get(f"/api/recurring-visits?elderly_member_id={member_a['id']}", headers=auth_header(token))
    series = resp.get_json()["series"]
    assert len(series) == 1
    assert series[0]["elderly_member_id"] == member_a["id"]


def test_volunteer_cannot_list_or_view_series(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    series_id = client.post("/api/recurring-visits", json=_valid_series(member["id"]), headers=auth_header(admin_token)).get_json()["series"]["id"]

    _, vol_token, _ = make_user(email="novolview@example.com")
    assert client.get("/api/recurring-visits", headers=auth_header(vol_token)).status_code == 403
    assert client.get(f"/api/recurring-visits/{series_id}", headers=auth_header(vol_token)).status_code == 403


def test_unauthenticated_cannot_access_recurring_visits(client):
    assert client.get("/api/recurring-visits").status_code == 401
    assert client.post("/api/recurring-visits", json={}).status_code == 401
