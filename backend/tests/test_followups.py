def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


# ---------- Auto-creation from source modules ----------

def test_health_follow_up_required_auto_creates_a_followup(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)

    resp = client.post(
        "/api/health-records", json={"elderly_member_id": member["id"], "follow_up_required": True, "follow_up_notes": "Recheck blood pressure"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201

    followups = client.get("/api/followups", headers=auth_header(token)).get_json()["followups"]
    assert len(followups) == 1
    assert followups[0]["source_type"] == "health_record"
    assert followups[0]["reason"] == "Recheck blood pressure"
    assert followups[0]["status"] == "Pending"


def test_health_follow_up_not_required_creates_nothing(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/health-records", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert client.get("/api/followups", headers=auth_header(token)).get_json()["followups"] == []


def test_home_visit_follow_up_defaults_assignee_to_the_visits_assignee(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, token)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Check", "assigned_to_id": vol_user["id"]}, headers=auth_header(token)).get_json()["visit"]

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed", "follow_up_required": True, "follow_up_notes": "Needs a nurse visit"}, headers=auth_header(vol_token))
    assert resp.status_code == 200

    followups = client.get("/api/followups", headers=auth_header(token)).get_json()["followups"]
    assert len(followups) == 1
    assert followups[0]["source_type"] == "home_visit"
    assert followups[0]["assigned_to_id"] == vol_user["id"]


def test_follow_up_not_recreated_on_repeated_true(client, make_staff_user, auth_header):
    """Re-saving an already-True follow_up_required must not create a
    second follow-up — only the False->True transition does."""
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    record = client.post("/api/health-records", json={"elderly_member_id": member["id"], "follow_up_required": True}, headers=auth_header(token)).get_json()["record"]

    client.patch(f"/api/health-records/{record['id']}", json={"follow_up_required": True, "mood": "Fair"}, headers=auth_header(token))
    assert len(client.get("/api/followups", headers=auth_header(token)).get_json()["followups"]) == 1


def test_assistance_request_follow_up_auto_creates(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Transportation", "description": "Clinic run"}, headers=auth_header(token)).get_json()["request"]
    client.patch(f"/api/assistance-requests/{req['id']}", json={"follow_up_required": True, "follow_up_notes": "Book next appointment"}, headers=auth_header(token))

    followups = client.get("/api/followups", headers=auth_header(token)).get_json()["followups"]
    assert len(followups) == 1
    assert followups[0]["source_type"] == "assistance_request"


def test_incident_follow_up_auto_creates_on_create_and_update(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], "incident_type": "Fall", "description": "Fell in the hallway", "follow_up_required": True, "follow_up_notes": "Check with GP"}, headers=auth_header(token))
    assert resp.status_code == 201
    followups = client.get("/api/followups", headers=auth_header(token)).get_json()["followups"]
    assert len(followups) == 1
    assert followups[0]["source_type"] == "incident"


# ---------- Manual creation, CRUD ----------

def test_admin_can_manually_create_followup(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "Family requested a call back", "priority": "High"}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["followup"]
    assert body["source_type"] == "manual"
    assert body["priority"] == "High"


def test_volunteer_cannot_manually_create_followup(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/followups", json={"elderly_member_id": 1, "reason": "x"}, headers=auth_header(token))
    assert resp.status_code == 403


def test_cannot_assign_followup_to_unverified_volunteer(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_user, _, _ = make_user(email="unverified-fu@example.com")
    resp = client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Authorization ----------

def test_volunteer_sees_only_their_own_followups(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, token, email="fu-a@example.com")
    _, vol_b_token = _verified_volunteer(client, make_user, auth_header, token, email="fu-b@example.com")

    client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "For A", "assigned_to_id": vol_a["id"]}, headers=auth_header(token))
    client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "Unassigned"}, headers=auth_header(token))

    mine = client.get("/api/followups", headers=auth_header(vol_a_token)).get_json()["followups"]
    assert len(mine) == 1
    assert mine[0]["reason"] == "For A"

    others = client.get("/api/followups", headers=auth_header(vol_b_token)).get_json()["followups"]
    assert others == []


def test_volunteer_cannot_access_another_volunteers_followup_by_id(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_a, _ = _verified_volunteer(client, make_user, auth_header, token, email="fu-c@example.com")
    _, vol_b_token = _verified_volunteer(client, make_user, auth_header, token, email="fu-d@example.com")
    fu = client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "For A", "assigned_to_id": vol_a["id"]}, headers=auth_header(token)).get_json()["followup"]

    resp = client.get(f"/api/followups/{fu['id']}", headers=auth_header(vol_b_token))
    assert resp.status_code == 403

    resp = client.patch(f"/api/followups/{fu['id']}", json={"status": "In Progress"}, headers=auth_header(vol_b_token))
    assert resp.status_code == 403


def test_volunteer_cannot_reassign_or_change_priority_on_own_followup(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, token, email="fu-e@example.com")
    fu = client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "For A", "assigned_to_id": vol_a["id"]}, headers=auth_header(token)).get_json()["followup"]

    resp = client.patch(f"/api/followups/{fu['id']}", json={"priority": "Urgent"}, headers=auth_header(vol_a_token))
    assert resp.status_code == 400
    resp = client.patch(f"/api/followups/{fu['id']}", json={"assigned_to_id": vol_a["id"]}, headers=auth_header(vol_a_token))
    assert resp.status_code == 400


def test_volunteer_can_progress_and_complete_own_followup(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, token, email="fu-f@example.com")
    fu = client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "For A", "assigned_to_id": vol_a["id"]}, headers=auth_header(token)).get_json()["followup"]

    resp = client.patch(f"/api/followups/{fu['id']}", json={"status": "Completed", "notes": "Done"}, headers=auth_header(vol_a_token))
    assert resp.status_code == 200
    body = resp.get_json()["followup"]
    assert body["status"] == "Completed"
    assert body["completed_at"] is not None


def test_unauthenticated_cannot_list_followups(client):
    assert client.get("/api/followups").status_code == 401


# ---------- Overdue filter ----------

def test_overdue_filter(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "Overdue one", "due_date": "2020-01-01"}, headers=auth_header(token))
    client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "Future one", "due_date": "2099-01-01"}, headers=auth_header(token))
    client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "No due date"}, headers=auth_header(token))

    overdue = client.get("/api/followups?overdue=true", headers=auth_header(token)).get_json()["followups"]
    assert len(overdue) == 1
    assert overdue[0]["reason"] == "Overdue one"
    assert overdue[0]["is_overdue"] is True


def test_completed_followup_is_never_overdue(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    fu = client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "x", "due_date": "2020-01-01"}, headers=auth_header(token)).get_json()["followup"]
    client.patch(f"/api/followups/{fu['id']}", json={"status": "Completed"}, headers=auth_header(token))

    overdue = client.get("/api/followups?overdue=true", headers=auth_header(token)).get_json()["followups"]
    assert overdue == []
