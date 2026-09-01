from datetime import timedelta

from app.extensions import db
from app.models import HomeVisit, utcnow

VALID_REASON = {"reason": "Unable to attend the centre due to mobility issues"}


def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="hours-vol@example.com"):
    user, access_token, _ = make_user(email=email, name="Hours Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _completed_visit(app, client, admin_token, auth_header, vol, member, started, completed):
    """Creates a visit assigned to `vol` and backdates started_at/
    completed_at directly — the real API only ever sets these to "now" at
    the instant of the status transition, so a test needing a specific,
    multi-hour gap has to set it directly, same technique already used
    for RecurringVisitSeries in test_recurring_visits.py."""
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]
    with app.app_context():
        row = db.session.get(HomeVisit, visit["id"])
        row.status = "Completed"
        row.started_at = started
        row.completed_at = completed
        db.session.commit()
    return visit["id"]


# ---------- Automatic hours: correctness ----------

def test_completed_visit_with_a_two_hour_gap_counts_as_120_minutes(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    now = utcnow()
    _completed_visit(app, client, admin_token, auth_header, vol, member, now - timedelta(hours=2), now)

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(vol_token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 120
    assert summary["automatic_minutes_lifetime"] == 120


def test_two_completed_visits_sum_without_double_counting(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    now = utcnow()
    _completed_visit(app, client, admin_token, auth_header, vol, member, now - timedelta(hours=1), now)
    _completed_visit(app, client, admin_token, auth_header, vol, member, now - timedelta(minutes=30), now)

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(vol_token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 90  # 60 + 30, each counted exactly once

    # Fetching again must not change the total — no accidental re-summing/duplication.
    summary_again = client.get("/api/volunteers/me/hours", headers=auth_header(vol_token)).get_json()["hours"]
    assert summary_again["minutes_lifetime"] == 90


def test_incomplete_assignment_does_not_count(client, app, make_user, make_staff_user, auth_header):
    """A visit that's Assigned/Started but never Completed — or Completed
    with no started_at (shouldn't happen via the real API, but the
    exclusion rule must hold defensively) — contributes zero minutes."""
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]
    client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Started"}, headers=auth_header(vol_token))

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(vol_token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 0


def test_negative_duration_is_never_counted(client, app, make_user, make_staff_user, auth_header):
    """Defensive: even if completed_at somehow ends up before started_at
    (bad data, a bug elsewhere, direct DB manipulation), the hours
    calculation must never produce a negative or nonsensical positive
    number from it."""
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    now = utcnow()
    _completed_visit(app, client, admin_token, auth_header, vol, member, now, now - timedelta(hours=1))  # completed BEFORE started

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(vol_token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 0


def test_zero_duration_is_not_counted(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    now = utcnow()
    _completed_visit(app, client, admin_token, auth_header, vol, member, now, now)

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(vol_token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 0


def test_cancelled_assignment_does_not_count_even_with_timestamps(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    now = utcnow()
    visit_id = _completed_visit(app, client, admin_token, auth_header, vol, member, now - timedelta(hours=1), now)
    with app.app_context():
        row = db.session.get(HomeVisit, visit_id)
        row.status = "Cancelled"  # e.g. incorrectly marked complete, then corrected
        db.session.commit()

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(vol_token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 0


def test_lifetime_hours_include_visits_outside_this_month(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    old = utcnow() - timedelta(days=200)
    _completed_visit(app, client, admin_token, auth_header, vol, member, old - timedelta(hours=3), old)

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(vol_token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 180
    assert summary["minutes_this_month"] == 0  # too long ago to count this month


# ---------- Manual hours: submission, review, authorization ----------

def test_volunteer_can_submit_manual_hours(client, make_user, auth_header):
    _, token, _ = make_user(email="manual-hours@example.com")
    resp = client.post("/api/volunteers/me/hours", json={"date": "2026-08-20", "duration_minutes": 90, "category": "Administrative", "description": "Prepared donation letters"}, headers=auth_header(token))
    assert resp.status_code == 201
    entry = resp.get_json()["entry"]
    assert entry["status"] == "Pending"
    assert entry["duration_minutes"] == 90


def test_manual_hours_rejects_future_date(client, make_user, auth_header):
    _, token, _ = make_user(email="future-hours@example.com")
    resp = client.post("/api/volunteers/me/hours", json={"date": "2099-01-01", "duration_minutes": 60}, headers=auth_header(token))
    assert resp.status_code == 400


def test_manual_hours_rejects_zero_or_negative_duration(client, make_user, auth_header):
    _, token, _ = make_user(email="badminutes@example.com")
    resp = client.post("/api/volunteers/me/hours", json={"date": "2026-08-20", "duration_minutes": 0}, headers=auth_header(token))
    assert resp.status_code == 400


def test_pending_manual_hours_do_not_count_toward_totals(client, make_user, auth_header):
    _, token, _ = make_user(email="pending-hours@example.com")
    client.post("/api/volunteers/me/hours", json={"date": "2026-08-20", "duration_minutes": 90}, headers=auth_header(token))
    summary = client.get("/api/volunteers/me/hours", headers=auth_header(token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 0


def test_admin_can_approve_manual_hours_and_it_then_counts(client, make_user, make_staff_user, auth_header):
    _, token, _ = make_user(email="approve-hours@example.com")
    _, admin_token = make_staff_user("admin")
    entry_id = client.post("/api/volunteers/me/hours", json={"date": "2026-08-20", "duration_minutes": 90}, headers=auth_header(token)).get_json()["entry"]["id"]

    resp = client.patch(f"/api/volunteers/hours/{entry_id}", json={"status": "Approved"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["entry"]["status"] == "Approved"

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 90
    assert summary["approved_manual_minutes_lifetime"] == 90


def test_admin_can_reject_manual_hours_with_reason(client, make_user, make_staff_user, auth_header):
    _, token, _ = make_user(email="reject-hours@example.com")
    _, admin_token = make_staff_user("admin")
    entry_id = client.post("/api/volunteers/me/hours", json={"date": "2026-08-20", "duration_minutes": 90}, headers=auth_header(token)).get_json()["entry"]["id"]

    resp = client.patch(f"/api/volunteers/hours/{entry_id}", json={"status": "Rejected", "rejection_reason": "No supporting detail"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["entry"]["rejection_reason"] == "No supporting detail"

    summary = client.get("/api/volunteers/me/hours", headers=auth_header(token)).get_json()["hours"]
    assert summary["minutes_lifetime"] == 0


def test_cannot_review_an_already_reviewed_entry(client, make_user, make_staff_user, auth_header):
    _, token, _ = make_user(email="doublereview@example.com")
    _, admin_token = make_staff_user("admin")
    entry_id = client.post("/api/volunteers/me/hours", json={"date": "2026-08-20", "duration_minutes": 90}, headers=auth_header(token)).get_json()["entry"]["id"]
    client.patch(f"/api/volunteers/hours/{entry_id}", json={"status": "Approved"}, headers=auth_header(admin_token))

    resp = client.patch(f"/api/volunteers/hours/{entry_id}", json={"status": "Rejected", "rejection_reason": "x"}, headers=auth_header(admin_token))
    assert resp.status_code == 409


def test_volunteer_cannot_approve_their_own_manual_hours(client, make_user, auth_header):
    _, token, _ = make_user(email="selfapprove@example.com")
    entry_id = client.post("/api/volunteers/me/hours", json={"date": "2026-08-20", "duration_minutes": 90}, headers=auth_header(token)).get_json()["entry"]["id"]
    resp = client.patch(f"/api/volunteers/hours/{entry_id}", json={"status": "Approved"}, headers=auth_header(token))
    assert resp.status_code == 403


def test_volunteer_cannot_see_another_volunteers_hours(client, make_user, auth_header):
    _, token_a, _ = make_user(email="hours-a@example.com")
    _, token_b, _ = make_user(email="hours-b@example.com")
    client.post("/api/volunteers/me/hours", json={"date": "2026-08-20", "duration_minutes": 90}, headers=auth_header(token_a))

    entries_b = client.get("/api/volunteers/me/hours/entries", headers=auth_header(token_b)).get_json()["entries"]
    assert entries_b == []


def test_staff_can_view_a_specific_volunteers_hours(client, make_user, make_staff_user, auth_header):
    user, token, _ = make_user(email="staffview-hours@example.com")
    _, admin_token = make_staff_user("admin")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "staffview-hours@example.com")["id"]

    _, staff_token = make_staff_user("staff", email="hoursstaff@example.com")
    resp = client.get(f"/api/volunteers/{vid}/hours", headers=auth_header(staff_token))
    assert resp.status_code == 200


def test_volunteer_cannot_view_hours_endpoint_for_another_volunteer_id(client, make_user, make_staff_user, auth_header):
    user, _, _ = make_user(email="targetid-hours@example.com")
    _, admin_token = make_staff_user("admin")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "targetid-hours@example.com")["id"]

    _, other_token, _ = make_user(email="nosy-hours@example.com")
    resp = client.get(f"/api/volunteers/{vid}/hours", headers=auth_header(other_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_hours(client):
    assert client.get("/api/volunteers/me/hours").status_code == 401
