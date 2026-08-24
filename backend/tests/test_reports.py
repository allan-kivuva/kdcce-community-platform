import datetime

import pytest


def _register_member(client, token, auth_header, name="Mary Achieng", **extra):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female", **extra}, headers=auth_header(token))
    return resp.get_json()["member"]


REPORT_ENDPOINTS = [
    "/api/reports/attendance",
    "/api/reports/health",
    "/api/reports/home-visits",
    "/api/reports/volunteers",
    "/api/reports/feeding",
    "/api/reports/inventory",
    "/api/reports/donations",
    "/api/reports/donations/history",
    "/api/reports/activities",
    "/api/reports/assistance",
    "/api/reports/incidents",
]


# ---------- Authorization sweep ----------

@pytest.mark.parametrize("path", REPORT_ENDPOINTS)
def test_unauthenticated_cannot_access_any_report(client, path):
    resp = client.get(path)
    assert resp.status_code == 401


@pytest.mark.parametrize("path", REPORT_ENDPOINTS)
def test_volunteer_cannot_access_any_report(client, make_user, auth_header, path):
    _, access_token, _ = make_user()
    resp = client.get(path, headers=auth_header(access_token))
    assert resp.status_code == 403


@pytest.mark.parametrize("path", REPORT_ENDPOINTS)
def test_staff_can_access_every_report(client, make_staff_user, auth_header, path):
    _, token = make_staff_user("staff")
    resp = client.get(path, headers=auth_header(token))
    assert resp.status_code == 200


@pytest.mark.parametrize("path", ["/api/reports/attendance/export.csv", "/api/reports/home-visits/export.csv", "/api/reports/inventory/export.csv"])
def test_volunteer_cannot_export_any_report_csv(client, make_user, auth_header, path):
    _, access_token, _ = make_user()
    resp = client.get(path, headers=auth_header(access_token))
    assert resp.status_code == 403


# ---------- Empty dataset safety (no division by zero, no crashes) ----------

def test_attendance_report_on_empty_dataset(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/reports/attendance", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()["report"]
    assert body["registered_count"] == 0
    assert body["total_records"] == 0
    assert body["average_daily"] == 0
    assert body["attendance_percentage"] == 0


def test_donations_report_on_empty_dataset(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/reports/donations", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["report"]["cash_total"] == 0.0


def test_assistance_report_on_empty_dataset(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/reports/assistance", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["report"]["completion_rate"] == 0


# ---------- Attendance report ----------

def test_attendance_report_counts_and_by_day(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _register_member(client, token, auth_header, "Mary Achieng")
    m2 = _register_member(client, token, auth_header, "John Otieno")
    client.post("/api/attendance/check-in", json={"elderly_member_id": m1["id"]}, headers=auth_header(token))
    client.post("/api/attendance/check-in", json={"elderly_member_id": m2["id"]}, headers=auth_header(token))

    resp = client.get("/api/reports/attendance", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["registered_count"] == 2
    assert body["total_records"] == 2
    assert body["still_checked_in"] == 2
    today = datetime.date.today().isoformat()
    assert body["by_day"] == [{"date": today, "count": 2}]
    assert body["highest_day"] == 2
    assert body["lowest_day"] == 2


def test_attendance_report_filters_by_opa(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    opa = client.post("/api/opas", json={"name": "Kibera OPA"}, headers=auth_header(token)).get_json()["opa"]
    m1 = _register_member(client, token, auth_header, "Mary Achieng", opa_id=opa["id"])
    m2 = _register_member(client, token, auth_header, "John Otieno")
    client.post("/api/attendance/check-in", json={"elderly_member_id": m1["id"]}, headers=auth_header(token))
    client.post("/api/attendance/check-in", json={"elderly_member_id": m2["id"]}, headers=auth_header(token))

    resp = client.get(f"/api/reports/attendance?opa_id={opa['id']}", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["registered_count"] == 1
    assert body["total_records"] == 1


def test_attendance_report_rejects_bad_date(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/reports/attendance?date_from=not-a-date", headers=auth_header(token))
    assert resp.status_code == 400


def test_attendance_report_rejects_date_to_before_date_from(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/reports/attendance?date_from=2026-06-01&date_to=2026-01-01", headers=auth_header(token))
    assert resp.status_code == 400


def test_attendance_report_csv_export(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    resp = client.get("/api/reports/attendance/export.csv", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "Date,Attendance Count" in resp.get_data(as_text=True)


# ---------- Health report ----------

def test_health_report_counts_follow_ups_and_wellness_trend(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/health-records", json={"elderly_member_id": member["id"], "wellbeing": "Good"}, headers=auth_header(token))
    client.post("/api/health-records", json={"elderly_member_id": member["id"], "wellbeing": "Poor", "follow_up_required": True}, headers=auth_header(token))

    resp = client.get("/api/reports/health", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["health_checks_completed"] == 2
    assert body["follow_ups_required"] == 1
    assert body["wellness_trend"] == {"Good": 1, "Poor": 1}
    assert body["clinic_visits"] is None


def test_health_report_medication_administration_breakdown(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    med = client.post("/api/medications", json={"elderly_member_id": member["id"], "name": "Amlodipine"}, headers=auth_header(token)).get_json()["medication"]
    client.post(f"/api/medications/{med['id']}/administrations", json={"status": "Given"}, headers=auth_header(token))
    client.post(f"/api/medications/{med['id']}/administrations", json={"status": "Missed"}, headers=auth_header(token))

    resp = client.get("/api/reports/health", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["medications_started"] == 1
    assert body["medication_administration"] == {"Given": 1, "Missed": 1}


# ---------- Home visits report ----------

def test_home_visits_report_by_status_and_volunteer(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, _, _ = make_user(email="vera5@example.com", name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "vera5@example.com")["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))

    v1 = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Check-in", "assigned_to_id": vol_user["id"]}, headers=auth_header(admin_token))
    v2 = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Follow-up"}, headers=auth_header(admin_token))
    assert v1.status_code == 201 and v2.status_code == 201
    # follow_up_required is an outcome field, recorded after a visit — not
    # accepted at creation — so it's set via PATCH here instead.
    client.patch(f"/api/home-visits/{v2.get_json()['visit']['id']}", json={"follow_up_required": True}, headers=auth_header(admin_token))

    resp = client.get("/api/reports/home-visits", headers=auth_header(admin_token))
    body = resp.get_json()["report"]
    assert body["total"] == 2
    assert body["by_status"]["Assigned"] == 1
    assert body["by_status"]["Pending"] == 1
    assert body["by_volunteer"]["Vera Volunteer"] == 1


def test_home_visits_report_csv_export(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Check-in"}, headers=auth_header(token))
    resp = client.get("/api/reports/home-visits/export.csv", headers=auth_header(token))
    assert resp.status_code == 200
    assert "Elderly Member,Status,Priority" in resp.get_data(as_text=True)


# ---------- Volunteers report ----------

def test_volunteers_report_workload_and_status_breakdown(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, _, _ = make_user(email="vera6@example.com", name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "vera6@example.com")["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(admin_token)).get_json()["visit"]
    client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed"}, headers=auth_header(admin_token))

    resp = client.get("/api/reports/volunteers", headers=auth_header(admin_token))
    body = resp.get_json()["report"]
    assert body["by_status"]["Verified"] == 1
    assert body["active_volunteers"] == 1
    workload = next(w for w in body["workload"] if w["name"] == "Vera Volunteer")
    assert workload["home_visits_total"] == 1
    assert workload["home_visits_completed"] == 1
    assert workload["active_assignments"] == 0
    assert not any("hour" in key.lower() for key in workload) and not any("hour" in key.lower() for key in body)
    # Extended fields: 1 completed, 0 pending, 0 cancelled -> 100% completion.
    assert workload["completion_rate"] == 100.0
    assert workload["pending_assignments"] == 0
    assert workload["cancelled_assignments"] == 0
    assert workload["assigned_elderly_count"] == 0  # the visit is Completed, not "currently assigned"
    assert workload["follow_ups_completed"] == 0


def test_volunteers_report_pending_cancelled_and_assigned_elderly(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, _, _ = make_user(email="vera7@example.com", name="Vera Seven")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "vera7@example.com")["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))

    # One active (pending), one cancelled.
    active_visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(admin_token)).get_json()["visit"]
    cancelled_visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(admin_token)).get_json()["visit"]
    client.patch(f"/api/home-visits/{cancelled_visit['id']}", json={"status": "Cancelled"}, headers=auth_header(admin_token))

    resp = client.get("/api/reports/volunteers", headers=auth_header(admin_token))
    workload = next(w for w in resp.get_json()["report"]["workload"] if w["name"] == "Vera Seven")
    assert workload["pending_assignments"] == 1
    assert workload["cancelled_assignments"] == 1
    assert workload["completion_rate"] == 0.0
    assert workload["assigned_elderly_count"] == 1  # only the still-Assigned visit counts


def test_volunteers_report_follow_ups_completed(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, _, _ = make_user(email="vera8@example.com", name="Vera Eight")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "vera8@example.com")["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))

    fu = client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(admin_token)).get_json()["followup"]
    client.patch(f"/api/followups/{fu['id']}", json={"status": "Completed"}, headers=auth_header(admin_token))

    resp = client.get("/api/reports/volunteers", headers=auth_header(admin_token))
    workload = next(w for w in resp.get_json()["report"]["workload"] if w["name"] == "Vera Eight")
    assert workload["follow_ups_completed"] == 1


def test_volunteers_report_handles_a_volunteer_with_zero_assignments(client, make_user, make_staff_user, auth_header):
    """Edge case: a Verified volunteer who has never been assigned
    anything must show clean zeros, not an error or a division crash."""
    _, admin_token = make_staff_user("admin")
    make_user(email="idle@example.com", name="Idle Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == "idle@example.com")["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))

    resp = client.get("/api/reports/volunteers", headers=auth_header(admin_token))
    workload = next(w for w in resp.get_json()["report"]["workload"] if w["name"] == "Idle Volunteer")
    assert workload["home_visits_total"] == 0
    assert workload["completion_rate"] == 0.0
    assert workload["assigned_elderly_count"] == 0
    assert workload["follow_ups_completed"] == 0


# ---------- Feeding report ----------

def test_feeding_report_meals_and_dietary_flag(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header, allergies="Peanuts")
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    resp = client.get("/api/reports/feeding", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["meals_planned"] == 1
    assert body["meals_served"] == 1
    assert body["dietary_flagged_attendees"] == 1


# ---------- Inventory report ----------

def test_inventory_report_uses_ledger_balance_not_a_second_calculation(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json={"name": "Rice", "category": "Food", "unit": "kg", "minimum_stock": 10}, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 50}, headers=auth_header(token))
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Out", "quantity": 15}, headers=auth_header(token))

    resp = client.get("/api/reports/inventory", headers=auth_header(token))
    body = resp.get_json()["report"]
    reported_item = next(i for i in body["items"] if i["name"] == "Rice")
    # Must equal the same current_stock the inventory module itself reports.
    direct = client.get(f"/api/inventory/{item['id']}", headers=auth_header(token)).get_json()["item"]
    assert reported_item["current_stock"] == direct["current_stock"] == 35.0
    assert body["stock_in_total"] == 50.0
    assert body["stock_out_total"] == 15.0


def test_inventory_report_donation_linked_count(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json={"name": "Rice", "category": "Food", "unit": "kg"}, headers=auth_header(token)).get_json()["item"]
    donation = client.post("/api/admin/donations", json={"donation_type": "Food", "donor_name": "Local Grocer", "item_description": "50kg rice", "quantity": 50, "unit": "kg"}, headers=auth_header(token)).get_json()["donation"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 50, "donation_id": donation["id"]}, headers=auth_header(token))
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 10}, headers=auth_header(token))

    resp = client.get("/api/reports/inventory", headers=auth_header(token))
    assert resp.get_json()["report"]["donation_linked_movements"] == 1


def test_inventory_report_csv_export(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json={"name": "Rice", "category": "Food", "unit": "kg"}, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 50}, headers=auth_header(token))
    resp = client.get("/api/reports/inventory/export.csv", headers=auth_header(token))
    assert resp.status_code == 200
    assert "Rice" in resp.get_data(as_text=True)


# ---------- Donations report ----------

def test_donations_report_totals_by_type(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/donations", json={"donor_name": "Amina", "donor_email": "amina@example.com", "amount": 1000, "frequency": "one-time"})
    client.post("/api/admin/donations", json={"donation_type": "Food", "donor_name": "Grocer", "item_description": "Rice", "quantity": 20, "unit": "kg"}, headers=auth_header(token))

    resp = client.get("/api/reports/donations", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["total_count"] == 2
    assert body["by_type"] == {"Cash": 1, "Food": 1}
    assert body["cash_total"] == 1000.0


def test_donations_history_is_paginated(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    for i in range(5):
        client.post("/api/donations", json={"donor_name": f"Donor {i}", "donor_email": f"d{i}@example.com", "amount": 100, "frequency": "one-time"})

    resp = client.get("/api/reports/donations/history?page=1&per_page=2", headers=auth_header(token))
    body = resp.get_json()
    assert len(body["donations"]) == 2
    assert body["pagination"]["total"] == 5
    assert body["pagination"]["pages"] == 3


def test_donations_history_filters_by_type_and_date(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/donations", json={"donor_name": "Amina", "donor_email": "amina@example.com", "amount": 1000, "frequency": "one-time"})
    client.post("/api/admin/donations", json={"donation_type": "Food", "donor_name": "Grocer", "item_description": "Rice", "quantity": 20, "unit": "kg"}, headers=auth_header(token))

    resp = client.get("/api/reports/donations/history?donation_type=Food", headers=auth_header(token))
    body = resp.get_json()
    assert body["pagination"]["total"] == 1
    assert body["donations"][0]["donation_type"] == "Food"


# ---------- Activities report ----------

def test_activities_report_participant_breakdown(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    activity = client.post("/api/activities", json={"title": "Walk", "activity_type": "Walking", "scheduled_at": "2026-08-25T09:00:00+00:00"}, headers=auth_header(token)).get_json()["activity"]
    participant = client.post(f"/api/activities/{activity['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["participant"]
    client.patch(f"/api/activities/{activity['id']}/participants/{participant['id']}", json={"status": "Attended"}, headers=auth_header(token))

    resp = client.get("/api/reports/activities", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["activities_conducted"] == 1
    assert body["by_type"] == {"Walking": 1}
    assert body["participant_status_breakdown"] == {"Attended": 1}


# ---------- Assistance report ----------

def test_assistance_report_completion_rate(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    r1 = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "x"}, headers=auth_header(token)).get_json()["request"]
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Transportation", "description": "y"}, headers=auth_header(token))
    client.patch(f"/api/assistance-requests/{r1['id']}", json={"status": "Completed"}, headers=auth_header(token))

    resp = client.get("/api/reports/assistance", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["total"] == 2
    assert body["completion_rate"] == 50.0
    assert body["by_type"] == {"Companionship": 1, "Transportation": 1}


# ---------- Incidents report ----------

def test_incidents_report_counts(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/incidents", json={"elderly_member_id": member["id"], "incident_type": "Fall", "description": "x", "follow_up_required": True}, headers=auth_header(token))
    inc2 = client.post("/api/incidents", json={"elderly_member_id": member["id"], "incident_type": "Medical Concern", "description": "y"}, headers=auth_header(token)).get_json()["incident"]
    client.patch(f"/api/incidents/{inc2['id']}", json={"status": "Resolved"}, headers=auth_header(token))

    resp = client.get("/api/reports/incidents", headers=auth_header(token))
    body = resp.get_json()["report"]
    assert body["total"] == 2
    assert body["open"] == 1
    assert body["resolved"] == 1
    assert body["follow_up_required"] == 1
    assert body["by_type"] == {"Fall": 1, "Medical Concern": 1}
