from datetime import timedelta

from app.models import utcnow

EXPECTED_KEYS = {
    "generated_at",
    "period_start",
    "unresolved_incidents",
    "upcoming_visits_7d",
    "approved_volunteer_hours_this_month",
    "program_attendance_this_month",
    "donations_total_this_month",
    "expenses_total_this_month",
    "low_stock_item_count",
    "meals_served_this_month",
}


def _member(client, token, auth_header, name="Mary Achieng"):
    return client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token)).get_json()["member"]


def test_operational_summary_returns_expected_shape(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/reports/operational-summary", headers=auth_header(token))
    assert resp.status_code == 200
    report = resp.get_json()["report"]
    assert set(report.keys()) == EXPECTED_KEYS


def test_operational_summary_reflects_seeded_data(client, make_staff_user, make_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)

    # One unresolved Incident (status defaults to "Open").
    incident_resp = client.post(
        "/api/incidents",
        json={"elderly_member_id": member["id"], "incident_type": "Fall", "description": "Slipped in the hallway"},
        headers=auth_header(token),
    )
    assert incident_resp.status_code == 201
    assert incident_resp.get_json()["incident"]["status"] == "Open"

    # One HomeVisit scheduled within the next 7 days, status "Pending" (the create default).
    scheduled_at = (utcnow() + timedelta(days=2)).isoformat()
    visit_resp = client.post(
        "/api/home-visits",
        json={"elderly_member_id": member["id"], "reason": "Wellbeing check", "scheduled_at": scheduled_at},
        headers=auth_header(token),
    )
    assert visit_resp.status_code == 201
    assert visit_resp.get_json()["visit"]["status"] == "Pending"

    # One Approved VolunteerHours row dated today (this month).
    _, vol_token, _ = make_user(email="hours-vol@example.com", name="Hours Volunteer")
    submit_resp = client.post(
        "/api/volunteers/me/hours",
        json={"date": utcnow().date().isoformat(), "duration_minutes": 120, "category": "Home Visit"},
        headers=auth_header(vol_token),
    )
    assert submit_resp.status_code == 201
    hours_id = submit_resp.get_json()["entry"]["id"]
    review_resp = client.patch(f"/api/volunteers/hours/{hours_id}", json={"status": "Approved"}, headers=auth_header(token))
    assert review_resp.status_code == 200

    resp = client.get("/api/reports/operational-summary", headers=auth_header(token))
    report = resp.get_json()["report"]
    assert report["unresolved_incidents"] >= 1
    assert report["upcoming_visits_7d"] >= 1
    assert report["approved_volunteer_hours_this_month"] >= 2.0  # 120 minutes = 2.0 hours


# ---------- Access control ----------

def test_volunteer_cannot_access_operational_summary(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.get("/api/reports/operational-summary", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_operational_summary(client):
    resp = client.get("/api/reports/operational-summary")
    assert resp.status_code == 401


# ---------- CLI command ----------

def test_generate_operational_report_cli_command(app, client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    client.post(
        "/api/incidents",
        json={"elderly_member_id": member["id"], "incident_type": "Fall", "description": "Slipped in the hallway"},
        headers=auth_header(token),
    )

    runner = app.test_cli_runner()
    result = runner.invoke(args=["generate-operational-report"])
    assert result.exit_code == 0
    assert "unresolved_incidents" in result.output
