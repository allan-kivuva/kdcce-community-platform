def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


VALID = {"incident_type": "Fall", "description": "Slipped in the dining hall"}


def test_staff_can_report_incident(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["incident"]
    assert body["status"] == "Open"
    assert body["emergency_contact_notified"] is False
    assert body["follow_up_required"] is False
    assert "occurred_at" in body


def test_volunteer_cannot_report_incident(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("admin")
    member = _register_member(client, staff_token, auth_header)
    _, access_token, _ = make_user()

    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_volunteer_cannot_list_incidents(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.get("/api/incidents", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_incidents(client):
    resp = client.get("/api/incidents")
    assert resp.status_code == 401


# ---------- Assignment ----------

def _verified_volunteer(client, make_user, auth_header, admin_token, email="incident-vol@example.com"):
    user, access_token, _ = make_user(email=email, name="Incident Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def test_staff_can_create_incident_pre_assigned(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, staff_token = make_staff_user("staff", email="assignee@example.com")
    member = _register_member(client, admin_token, auth_header)
    staff_user = client.get("/api/incidents/assignees", headers=auth_header(admin_token)).get_json()["assignees"]
    staff_id = next(a["id"] for a in staff_user if a["name"] == "Staffer")

    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], "assigned_to_id": staff_id, **VALID}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    body = resp.get_json()["incident"]
    assert body["assigned_to_id"] == staff_id
    assert body["assigned_to"] == "Staffer"


def test_admin_can_assign_an_existing_incident(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, staff_token = make_staff_user("staff", email="assignee2@example.com")
    member = _register_member(client, admin_token, auth_header)
    incident_id = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(admin_token)).get_json()["incident"]["id"]

    staff_id = next(a["id"] for a in client.get("/api/incidents/assignees", headers=auth_header(admin_token)).get_json()["assignees"] if a["name"] == "Staffer")
    resp = client.patch(f"/api/incidents/{incident_id}", json={"assigned_to_id": staff_id}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["incident"]["assigned_to_id"] == staff_id


def test_assignment_can_be_cleared(client, make_staff_user, auth_header):
    admin_user, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    incident_id = client.post("/api/incidents", json={"elderly_member_id": member["id"], "assigned_to_id": admin_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["incident"]["id"]

    resp = client.patch(f"/api/incidents/{incident_id}", json={"assigned_to_id": None}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["incident"]["assigned_to_id"] is None


def test_assignment_rejects_a_volunteer(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, _ = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], "assigned_to_id": vol["id"], **VALID}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_assignment_rejects_unknown_user(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], "assigned_to_id": 999999, **VALID}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_list_filters_by_assigned_to(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, _ = make_staff_user("staff", email="filterassignee@example.com")
    member = _register_member(client, admin_token, auth_header)
    staff_id = next(a["id"] for a in client.get("/api/incidents/assignees", headers=auth_header(admin_token)).get_json()["assignees"] if a["name"] == "Staffer")

    client.post("/api/incidents", json={"elderly_member_id": member["id"], "assigned_to_id": staff_id, **VALID}, headers=auth_header(admin_token))
    client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(admin_token))  # unassigned

    resp = client.get(f"/api/incidents?assigned_to_id={staff_id}", headers=auth_header(admin_token))
    incidents = resp.get_json()["incidents"]
    assert len(incidents) == 1
    assert incidents[0]["assigned_to_id"] == staff_id


def test_assignees_endpoint_lists_only_admin_and_staff(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, _ = make_staff_user("staff", email="listedstaff@example.com")
    _verified_volunteer(client, make_user, auth_header, admin_token, email="notlisted-vol@example.com")

    resp = client.get("/api/incidents/assignees", headers=auth_header(admin_token))
    assert resp.status_code == 200
    people = resp.get_json()["assignees"]
    assert all(p["role"] in ("admin", "staff") for p in people)
    assert "Incident Volunteer" not in [p["name"] for p in people]


def test_volunteer_cannot_list_incident_assignees(client, make_user, auth_header):
    _, token, _ = make_user(email="novolassignees@example.com")
    resp = client.get("/api/incidents/assignees", headers=auth_header(token))
    assert resp.status_code == 403


def test_staff_can_call_assignees_endpoint(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.get("/api/incidents/assignees", headers=auth_header(token))
    assert resp.status_code == 200


# ---------- Volunteer privacy is preserved (no new access granted) ----------

def test_volunteer_still_cannot_view_a_specific_incident(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    incident_id = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(admin_token)).get_json()["incident"]["id"]

    _, vol_token, _ = make_user(email="stillnoaccess@example.com")
    resp = client.get(f"/api/incidents/{incident_id}", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_assigning_an_incident_to_a_volunteer_is_impossible_even_indirectly(client, make_user, make_staff_user, auth_header):
    """Belt-and-braces: even if a caller tried assigning a concern to a
    volunteer through the update path (not just create), it's rejected —
    a volunteer must never end up as an incident's assignee by any route,
    since they have no way to ever retrieve it afterward."""
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="stillnoassign@example.com")
    incident_id = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(admin_token)).get_json()["incident"]["id"]

    resp = client.patch(f"/api/incidents/{incident_id}", json={"assigned_to_id": vol["id"]}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_create_rejects_unknown_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/incidents", json={"elderly_member_id": 999, **VALID}, headers=auth_header(token))
    assert resp.status_code == 400


def test_create_rejects_invalid_type(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], "incident_type": "Sunburn", "description": "x"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_create_rejects_missing_description(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], "incident_type": "Fall"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_can_record_full_details_on_create(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/incidents", json={
        "elderly_member_id": member["id"], **VALID,
        "location": "Dining hall", "immediate_action_taken": "Assisted to a chair, checked for injury",
        "emergency_contact_notified": True, "follow_up_required": True, "follow_up_notes": "Doctor visit tomorrow",
    }, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["incident"]
    assert body["location"] == "Dining hall"
    assert body["emergency_contact_notified"] is True
    assert body["follow_up_required"] is True


# ---------- Regressions: partial PATCH must not reset fields ----------

def test_status_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["incident"]
    client.patch(f"/api/incidents/{incident['id']}", json={"status": "Under Review"}, headers=auth_header(token))

    patched = client.patch(f"/api/incidents/{incident['id']}", json={"location": "Dining hall"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["incident"]["status"] == "Under Review"
    assert patched.get_json()["incident"]["location"] == "Dining hall"


def test_emergency_contact_notified_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID, "emergency_contact_notified": True}, headers=auth_header(token)).get_json()["incident"]

    patched = client.patch(f"/api/incidents/{incident['id']}", json={"description": "Updated account of the fall"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["incident"]["emergency_contact_notified"] is True


def test_follow_up_required_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID, "follow_up_required": True, "follow_up_notes": "Doctor visit tomorrow"}, headers=auth_header(token)).get_json()["incident"]

    patched = client.patch(f"/api/incidents/{incident['id']}", json={"status": "Resolved"}, headers=auth_header(token))
    assert patched.status_code == 200
    body = patched.get_json()["incident"]
    assert body["follow_up_required"] is True
    assert body["follow_up_notes"] == "Doctor visit tomorrow"


def test_occurred_at_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["incident"]
    original_occurred_at = incident["occurred_at"]

    patched = client.patch(f"/api/incidents/{incident['id']}", json={"resolution_notes": "No lasting injury"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["incident"]["occurred_at"] == original_occurred_at


# ---------- Resolution workflow ----------

def test_staff_can_resolve_an_incident(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["incident"]

    resp = client.patch(f"/api/incidents/{incident['id']}", json={"status": "Resolved", "resolution_notes": "Minor bruise, no further action needed"}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()["incident"]
    assert body["status"] == "Resolved"
    assert body["resolution_notes"] == "Minor bruise, no further action needed"


def test_resolving_an_incident_is_audited(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["incident"]

    resp = client.patch(
        f"/api/incidents/{incident['id']}",
        json={"status": "Resolved", "resolution_notes": "Minor bruise, no further action needed"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200

    logs_resp = client.get(
        f"/api/audit-logs?resource_type=incident&resource_id={incident['id']}", headers=auth_header(token)
    )
    logs = logs_resp.get_json()["audit_logs"]
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "update"
    assert log["resource_id"] == incident["id"]
    assert log["before"]["status"] == "Open"
    assert log["after"]["status"] == "Resolved"
    assert log["after"]["resolution_notes"] == "Minor bruise, no further action needed"
    for snapshot in (log["before"], log["after"]):
        for key in snapshot:
            assert "password" not in key.lower()
            assert "token" not in key.lower()


def test_update_rejects_invalid_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["incident"]
    resp = client.patch(f"/api/incidents/{incident['id']}", json={"status": "Ignored"}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Filtering ----------

def test_list_filters_by_member_type_status_and_follow_up(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _register_member(client, token, auth_header, "Mary Achieng")
    m2 = _register_member(client, token, auth_header, "John Otieno")
    client.post("/api/incidents", json={"elderly_member_id": m1["id"], "incident_type": "Fall", "description": "x", "follow_up_required": True}, headers=auth_header(token))
    client.post("/api/incidents", json={"elderly_member_id": m2["id"], "incident_type": "Medical Concern", "description": "y", "follow_up_required": False}, headers=auth_header(token))

    by_member = client.get(f"/api/incidents?elderly_member_id={m1['id']}", headers=auth_header(token))
    assert len(by_member.get_json()["incidents"]) == 1

    by_type = client.get("/api/incidents?incident_type=Medical+Concern", headers=auth_header(token))
    assert len(by_type.get_json()["incidents"]) == 1

    follow_up = client.get("/api/incidents?follow_up_required=true", headers=auth_header(token))
    names = [i["elderly_member_name"] for i in follow_up.get_json()["incidents"]]
    assert names == ["Mary Achieng"]


# ---------- No delete ----------

def test_incidents_have_no_delete_endpoint(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["incident"]

    resp = client.delete(f"/api/incidents/{incident['id']}", headers=auth_header(token))
    assert resp.status_code == 405  # method not allowed — no route exists for it, even for admin


# ---------- Severity ----------

def test_severity_defaults_to_medium(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token))
    assert resp.get_json()["incident"]["severity"] == "Medium"


def test_severity_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], "severity": "High", **VALID}, headers=auth_header(token)).get_json()["incident"]

    patched = client.patch(f"/api/incidents/{incident['id']}", json={"status": "Under Review"}, headers=auth_header(token))
    assert patched.get_json()["incident"]["severity"] == "High"


def test_rejects_invalid_severity(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], "severity": "Catastrophic", **VALID}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Critical incident notifications ----------

def test_critical_incident_notifies_every_admin_and_staff(client, make_staff_user, auth_header):
    admin_user, admin_token = make_staff_user("admin")
    staff_user, staff_token = make_staff_user("staff", email="critical-staff@example.com")
    member = _register_member(client, admin_token, auth_header)

    resp = client.post("/api/incidents", json={"elderly_member_id": member["id"], "severity": "Critical", **VALID}, headers=auth_header(admin_token))
    assert resp.status_code == 201

    for token in (admin_token, staff_token):
        notifications = client.get("/api/notifications?notification_type=Critical%20Incident", headers=auth_header(token)).get_json()["notifications"]
        assert len(notifications) == 1


def test_non_critical_incident_does_not_notify(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    client.post("/api/incidents", json={"elderly_member_id": member["id"], "severity": "Low", **VALID}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications?notification_type=Critical%20Incident", headers=auth_header(admin_token)).get_json()["notifications"]
    assert notifications == []


def test_escalating_to_critical_via_patch_notifies(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], "severity": "Medium", **VALID}, headers=auth_header(admin_token)).get_json()["incident"]

    client.patch(f"/api/incidents/{incident['id']}", json={"severity": "Critical"}, headers=auth_header(admin_token))
    notifications = client.get("/api/notifications?notification_type=Critical%20Incident", headers=auth_header(admin_token)).get_json()["notifications"]
    assert len(notifications) == 1


def test_resaving_already_critical_does_not_renotify(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    incident = client.post("/api/incidents", json={"elderly_member_id": member["id"], "severity": "Critical", **VALID}, headers=auth_header(admin_token)).get_json()["incident"]

    client.patch(f"/api/incidents/{incident['id']}", json={"severity": "Critical", "status": "Under Review"}, headers=auth_header(admin_token))
    notifications = client.get("/api/notifications?notification_type=Critical%20Incident", headers=auth_header(admin_token)).get_json()["notifications"]
    assert len(notifications) == 1
