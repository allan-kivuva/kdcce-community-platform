def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


VALID = {"request_type": "Companionship", "description": "Would like a weekly visitor"}


def test_staff_can_create_request(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["request"]
    assert body["status"] == "Requested"
    assert body["priority"] == "Medium"


def test_volunteer_cannot_create_request(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("admin")
    member = _register_member(client, staff_token, auth_header)
    _, access_token, _ = make_user()

    resp = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_create_rejects_unknown_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/assistance-requests", json={"elderly_member_id": 999, **VALID}, headers=auth_header(token))
    assert resp.status_code == 400


def test_create_rejects_invalid_type(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Karaoke", "description": "x"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_cannot_assign_to_unverified_volunteer(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    volunteer_user, _, _ = make_user(email="unverified@example.com")

    resp = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": volunteer_user["id"], **VALID}, headers=auth_header(token))
    assert resp.status_code == 400


def test_assigning_on_create_sets_status_assigned(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    volunteer_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": volunteer_user["id"], **VALID}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["request"]["status"] == "Assigned"


# ---------- List/get scoping ----------

def test_volunteer_sees_only_their_own_assigned_requests(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)

    mine = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(admin_token))  # unassigned, not theirs

    resp = client.get("/api/assistance-requests", headers=auth_header(vol_token))
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.get_json()["requests"]]
    assert ids == [mine["id"]]


def test_volunteer_cannot_view_a_request_not_assigned_to_them(client, make_staff_user, auth_header, make_user):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]
    _, vol_token, _ = make_user(email="outsider@example.com")

    resp = client.get(f"/api/assistance-requests/{req['id']}", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_rejected_volunteer_loses_access_to_previously_assigned_requests(client, make_user, make_staff_user, auth_header):
    """Same reasoning as the equivalent home-visits test: assigned_to_id
    isn't cleared on rejection, so access must be gated on current status,
    not just "am I the assignee.\""""
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="revoked-ar@example.com")
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]

    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    volunteer_id = next(v for v in volunteers if v["email"] == "revoked-ar@example.com")["id"]
    client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "Rejected"}, headers=auth_header(admin_token))

    assert client.get("/api/assistance-requests", headers=auth_header(vol_token)).status_code == 403
    assert client.get(f"/api/assistance-requests/{req['id']}", headers=auth_header(vol_token)).status_code == 403
    assert client.patch(f"/api/assistance-requests/{req['id']}", json={"status": "Completed"}, headers=auth_header(vol_token)).status_code == 403
    assert client.post(f"/api/assistance-requests/{req['id']}/accept", headers=auth_header(vol_token)).status_code == 403


def test_pending_volunteer_cannot_list_or_view_requests(client, make_user, auth_header):
    _, vol_token, _ = make_user(email="stillpending-ar@example.com")
    resp = client.get("/api/assistance-requests", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_staff_sees_all_and_can_filter(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _register_member(client, token, auth_header, "Mary Achieng")
    m2 = _register_member(client, token, auth_header, "John Otieno")
    client.post("/api/assistance-requests", json={"elderly_member_id": m1["id"], "priority": "Urgent", **VALID}, headers=auth_header(token))
    client.post("/api/assistance-requests", json={"elderly_member_id": m2["id"], "priority": "Low", **VALID}, headers=auth_header(token))

    urgent = client.get("/api/assistance-requests?priority=Urgent", headers=auth_header(token))
    names = [r["elderly_member_name"] for r in urgent.get_json()["requests"]]
    assert names == ["Mary Achieng"]


def test_unauthenticated_cannot_list_requests(client):
    resp = client.get("/api/assistance-requests")
    assert resp.status_code == 401


# ---------- Update scoping ----------

def test_staff_can_fully_edit_a_request(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["request"]

    resp = client.patch(f"/api/assistance-requests/{req['id']}", json={"priority": "High", "status": "Matching"}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()["request"]
    assert body["priority"] == "High"
    assert body["status"] == "Matching"


def test_assignee_cannot_set_status_to_accepted_via_patch(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]

    resp = client.patch(f"/api/assistance-requests/{req['id']}", json={"status": "Accepted"}, headers=auth_header(vol_token))
    assert resp.status_code == 400  # "Accepted" is not in the assignee-settable status list


def test_assignee_cannot_reassign_or_change_priority(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]

    resp = client.patch(f"/api/assistance-requests/{req['id']}", json={"priority": "Urgent"}, headers=auth_header(vol_token))
    assert resp.status_code == 400  # "priority" is not a field on the assignee schema


def test_volunteer_cannot_edit_a_request_not_assigned_to_them(client, make_staff_user, auth_header, make_user):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]
    _, vol_token, _ = make_user(email="outsider2@example.com")

    resp = client.patch(f"/api/assistance-requests/{req['id']}", json={"status": "In Progress"}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_status_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["request"]
    client.patch(f"/api/assistance-requests/{req['id']}", json={"status": "Matching"}, headers=auth_header(token))

    patched = client.patch(f"/api/assistance-requests/{req['id']}", json={"description": "Updated details"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["request"]["status"] == "Matching"


# ---------- Acceptance ----------

def test_assignee_can_accept_their_assigned_request(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]

    resp = client.post(f"/api/assistance-requests/{req['id']}/accept", headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["request"]["status"] == "Accepted"


def test_cannot_accept_a_request_not_assigned_to_you(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]
    _, other_token, _ = make_user(email="someoneelse@example.com")

    resp = client.post(f"/api/assistance-requests/{req['id']}/accept", headers=auth_header(other_token))
    assert resp.status_code == 403


def test_cannot_accept_an_unassigned_request(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["request"]  # status: Requested, no assignee

    resp = client.post(f"/api/assistance-requests/{req['id']}/accept", headers=auth_header(token))
    assert resp.status_code == 403  # nobody is assigned, so no one (including the creator) can accept it


def test_cannot_accept_twice(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]
    client.post(f"/api/assistance-requests/{req['id']}/accept", headers=auth_header(vol_token))

    resp = client.post(f"/api/assistance-requests/{req['id']}/accept", headers=auth_header(vol_token))
    assert resp.status_code == 409


def test_assignee_can_progress_and_complete_after_accepting(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID}, headers=auth_header(admin_token)).get_json()["request"]
    client.post(f"/api/assistance-requests/{req['id']}/accept", headers=auth_header(vol_token))

    in_progress = client.patch(f"/api/assistance-requests/{req['id']}", json={"status": "In Progress"}, headers=auth_header(vol_token))
    assert in_progress.status_code == 200

    completed = client.patch(f"/api/assistance-requests/{req['id']}", json={"status": "Completed", "outcome_notes": "Visited and had tea together"}, headers=auth_header(vol_token))
    assert completed.status_code == 200
    body = completed.get_json()["request"]
    assert body["status"] == "Completed"
    assert body["completed_at"] is not None
    assert body["outcome_notes"] == "Visited and had tea together"


# ---------- Home visit link ----------

def test_request_can_link_to_a_home_visit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Follow-up needed"}, headers=auth_header(token)).get_json()["visit"]

    resp = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "home_visit_id": visit["id"], **VALID}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["request"]["home_visit_id"] == visit["id"]


def test_request_rejects_unknown_home_visit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "home_visit_id": 999, **VALID}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Delete ----------

def test_admin_can_delete_request(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["request"]
    resp = client.delete(f"/api/assistance-requests/{req['id']}", headers=auth_header(token))
    assert resp.status_code == 204


def test_staff_cannot_delete_request(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], **VALID}, headers=auth_header(token)).get_json()["request"]
    resp = client.delete(f"/api/assistance-requests/{req['id']}", headers=auth_header(token))
    assert resp.status_code == 403
