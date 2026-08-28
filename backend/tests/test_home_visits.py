def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


VALID_REASON = {"reason": "Unable to attend the centre due to mobility issues"}


# ---------- Assignees ----------

def test_assignees_lists_staff_and_verified_volunteers_only(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, _ = make_staff_user("staff", email="caregiver2@example.com")
    make_user(email="unverified2@example.com")  # pending, should not appear
    _verified_volunteer(client, make_user, auth_header, admin_token, email="vera2@example.com")

    resp = client.get("/api/home-visits/assignees", headers=auth_header(admin_token))
    assert resp.status_code == 200
    names = {p["name"]: p["role"] for p in resp.get_json()["assignees"]}
    assert names.get("Vera Volunteer") == "volunteer"
    assert "unverified2@example.com" not in [p["name"] for p in resp.get_json()["assignees"]]
    assert any(role in ("admin", "staff") for role in names.values())


def test_volunteer_cannot_list_assignees(client, make_user, auth_header):
    _, access_token, _ = make_user(email="notallowed@example.com")
    resp = client.get("/api/home-visits/assignees", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_staff_can_create_a_visit_request(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["visit"]
    assert body["status"] == "Pending"
    assert body["priority"] == "Medium"
    assert body["elderly_member_name"] == "Mary Achieng"


def test_volunteer_cannot_create_a_visit_request(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("admin")
    member = _register_member(client, staff_token, auth_header)
    _, access_token, _ = make_user()

    resp = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_create_rejects_unknown_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/home-visits", json={"elderly_member_id": 999, **VALID_REASON}, headers=auth_header(token))
    assert resp.status_code == 400


def test_create_rejects_missing_reason(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/home-visits", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 400


def test_cannot_assign_to_unverified_volunteer(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    volunteer_user, _, _ = make_user(email="unverified@example.com")

    resp = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": volunteer_user["id"], **VALID_REASON}, headers=auth_header(token))
    assert resp.status_code == 400


def test_can_assign_to_verified_volunteer_and_status_becomes_assigned(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    volunteer_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": volunteer_user["id"], **VALID_REASON}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    body = resp.get_json()["visit"]
    assert body["status"] == "Assigned"
    assert body["assigned_to"] == "Vera Volunteer"


def test_can_assign_to_staff_directly(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    staff_user, _ = make_staff_user("staff", email="caregiver@example.com")

    resp = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": staff_user["id"], **VALID_REASON}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["visit"]["status"] == "Assigned"


# ---------- List/get scoping ----------

def test_volunteer_sees_only_their_own_assigned_visits(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)

    mine = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(admin_token))  # unassigned, not theirs

    resp = client.get("/api/home-visits", headers=auth_header(vol_token))
    assert resp.status_code == 200
    ids = [v["id"] for v in resp.get_json()["visits"]]
    assert ids == [mine["id"]]


def test_volunteer_cannot_view_a_visit_not_assigned_to_them(client, make_staff_user, auth_header, make_user):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]
    _, vol_token, _ = make_user(email="outsider@example.com")

    resp = client.get(f"/api/home-visits/{visit['id']}", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_rejected_volunteer_loses_access_to_previously_assigned_visits(client, make_user, make_staff_user, auth_header):
    """A volunteer who was Verified and assigned a visit, then later
    Rejected, must lose list/get/update access immediately — even though
    assigned_to_id still points at them (rejecting doesn't reassign or
    clear existing visits)."""
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="revoked@example.com")
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]

    vid = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    volunteer_id = next(v for v in vid if v["email"] == "revoked@example.com")["id"]
    client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "Rejected"}, headers=auth_header(admin_token))

    assert client.get("/api/home-visits", headers=auth_header(vol_token)).status_code == 403
    assert client.get(f"/api/home-visits/{visit['id']}", headers=auth_header(vol_token)).status_code == 403
    assert client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed"}, headers=auth_header(vol_token)).status_code == 403


def test_pending_volunteer_cannot_list_or_view_home_visits(client, make_user, auth_header):
    _, vol_token, _ = make_user(email="stillpending@example.com")
    resp = client.get("/api/home-visits", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_staff_sees_all_visits_and_can_filter(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _register_member(client, token, auth_header, "Mary Achieng")
    m2 = _register_member(client, token, auth_header, "John Otieno")
    client.post("/api/home-visits", json={"elderly_member_id": m1["id"], "priority": "Urgent", **VALID_REASON}, headers=auth_header(token))
    client.post("/api/home-visits", json={"elderly_member_id": m2["id"], "priority": "Low", **VALID_REASON}, headers=auth_header(token))

    urgent = client.get("/api/home-visits?priority=Urgent", headers=auth_header(token))
    names = [v["elderly_member_name"] for v in urgent.get_json()["visits"]]
    assert names == ["Mary Achieng"]


def test_unauthenticated_cannot_list_visits(client):
    resp = client.get("/api/home-visits")
    assert resp.status_code == 401


# ---------- Update scoping ----------

def test_staff_can_fully_edit_a_visit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(token)).get_json()["visit"]

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"priority": "High", "status": "Scheduled"}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()["visit"]
    assert body["priority"] == "High"
    assert body["status"] == "Scheduled"


def test_assigned_volunteer_can_record_outcome(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed", "observations": "Doing well", "support_provided": "Groceries delivered"}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    body = resp.get_json()["visit"]
    assert body["status"] == "Completed"
    assert body["observations"] == "Doing well"
    assert body["completed_at"] is not None


def test_assigned_volunteer_cannot_reassign_or_change_priority(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"priority": "Urgent"}, headers=auth_header(vol_token))
    assert resp.status_code == 400  # "priority" is not a field on the assignee schema


def test_volunteer_cannot_edit_a_visit_not_assigned_to_them(client, make_staff_user, auth_header, make_user):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]
    _, vol_token, _ = make_user(email="outsider2@example.com")

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed"}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_status_persists_across_partial_edit(client, make_staff_user, auth_header):
    """Regression: PATCHing without status must not reset it back to Pending."""
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(token)).get_json()["visit"]
    client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Scheduled"}, headers=auth_header(token))

    patched = client.patch(f"/api/home-visits/{visit['id']}", json={"observations": "Note"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["visit"]["status"] == "Scheduled"


def test_staff_cannot_assign_to_unverified_volunteer_via_patch(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(token)).get_json()["visit"]
    volunteer_user, _, _ = make_user(email="stillunverified@example.com")

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"assigned_to_id": volunteer_user["id"]}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Delete ----------

def test_admin_can_delete_visit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(token)).get_json()["visit"]
    resp = client.delete(f"/api/home-visits/{visit['id']}", headers=auth_header(token))
    assert resp.status_code == 204


def test_staff_cannot_delete_visit(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], **VALID_REASON}, headers=auth_header(token)).get_json()["visit"]
    resp = client.delete(f"/api/home-visits/{visit['id']}", headers=auth_header(token))
    assert resp.status_code == 403
