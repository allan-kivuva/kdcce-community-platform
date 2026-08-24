"""Tests for the volunteer field-work upgrade: assignment Start lifecycle,
home-visit checklist, "My Elderly Members" (scoped, IDOR-safe), and the
volunteer-restricted "Report a Concern" Incident create path."""

VALID_REASON = {"reason": "Unable to attend the centre due to mobility issues"}
VALID_ASSISTANCE = {"request_type": "Companionship", "description": "Would like a weekly visitor"}


def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com", name="Vera Volunteer"):
    user, access_token, _ = make_user(email=email, name=name)
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token, vid


def _make_visit(client, admin_token, auth_header, assignee_id, member=None):
    member = member or _register_member(client, admin_token, auth_header)
    resp = client.post(
        "/api/home-visits",
        json={"elderly_member_id": member["id"], "assigned_to_id": assignee_id, **VALID_REASON},
        headers=auth_header(admin_token),
    )
    return resp.get_json()["visit"]


def _make_assistance(client, admin_token, auth_header, assignee_id, member=None):
    member = member or _register_member(client, admin_token, auth_header)
    resp = client.post(
        "/api/assistance-requests",
        json={"elderly_member_id": member["id"], "assigned_to_id": assignee_id, **VALID_ASSISTANCE},
        headers=auth_header(admin_token),
    )
    return resp.get_json()["request"]


# ---------- Assignment lifecycle: Started ----------

def test_home_visit_started_at_is_server_set(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])
    assert visit["started_at"] is None

    # started_at isn't a field the assignee schema even accepts — a
    # client-supplied value is rejected outright, not silently ignored.
    rejected = client.patch(
        f"/api/home-visits/{visit['id']}", json={"status": "Started", "started_at": "2000-01-01T00:00:00Z"},
        headers=auth_header(vol_token),
    )
    assert rejected.status_code == 400

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Started"}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    body = resp.get_json()["visit"]
    assert body["status"] == "Started"
    assert body["started_at"] is not None


def test_home_visit_started_at_set_only_once(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    r1 = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Started"}, headers=auth_header(vol_token))
    first_started = r1.get_json()["visit"]["started_at"]
    r2 = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "In Progress"}, headers=auth_header(vol_token))
    assert r2.get_json()["visit"]["started_at"] == first_started


def test_assistance_request_started_at_is_server_set(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    req = _make_assistance(client, admin_token, auth_header, vol_user["id"])
    client.post(f"/api/assistance-requests/{req['id']}/accept", headers=auth_header(vol_token))

    rejected = client.patch(
        f"/api/assistance-requests/{req['id']}", json={"status": "Started", "started_at": "2000-01-01T00:00:00Z"},
        headers=auth_header(vol_token),
    )
    assert rejected.status_code == 400

    resp = client.patch(f"/api/assistance-requests/{req['id']}", json={"status": "Started"}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["request"]["started_at"] is not None


def test_volunteer_cannot_start_someone_elses_visit(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, _, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="a@example.com", name="A")
    _, vol_b_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="b@example.com", name="B")
    visit = _make_visit(client, admin_token, auth_header, vol_a["id"])

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Started"}, headers=auth_header(vol_b_token))
    assert resp.status_code == 403


# ---------- Home visit checklist ----------

def test_checklist_defaults_all_unchecked(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.get(f"/api/home-visits/{visit['id']}/checklist", headers=auth_header(vol_token))
    assert resp.status_code == 200
    items = resp.get_json()["checklist"]
    assert len(items) == 5
    assert all(not i["checked"] for i in items)


def test_checklist_toggle_and_unknown_item(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.patch(
        f"/api/home-visits/{visit['id']}/checklist", json={"item_key": "wellbeing", "checked": True},
        headers=auth_header(vol_token),
    )
    assert resp.status_code == 200
    items = {i["item_key"]: i for i in resp.get_json()["checklist"]}
    assert items["wellbeing"]["checked"] is True
    assert items["wellbeing"]["checked_at"] is not None

    bad = client.patch(
        f"/api/home-visits/{visit['id']}/checklist", json={"item_key": "not_a_real_item", "checked": True},
        headers=auth_header(vol_token),
    )
    assert bad.status_code == 400


def test_checklist_forbidden_for_unassigned_volunteer(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, _, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="a2@example.com", name="A2")
    _, vol_b_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="b2@example.com", name="B2")
    visit = _make_visit(client, admin_token, auth_header, vol_a["id"])

    resp = client.get(f"/api/home-visits/{visit['id']}/checklist", headers=auth_header(vol_b_token))
    assert resp.status_code == 403


# ---------- My Elderly Members ----------

def test_list_my_elderly_members_scoped_to_assignments(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, vol_a_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="ea@example.com", name="EA")
    vol_b, vol_b_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="eb@example.com", name="EB")
    _make_visit(client, admin_token, auth_header, vol_a["id"])

    resp_a = client.get("/api/volunteers/me/elderly-members", headers=auth_header(vol_a_token))
    assert resp_a.status_code == 200
    assert len(resp_a.get_json()["elderly_members"]) == 1

    resp_b = client.get("/api/volunteers/me/elderly-members", headers=auth_header(vol_b_token))
    assert resp_b.status_code == 200
    assert resp_b.get_json()["elderly_members"] == []


def test_elderly_member_snapshot_excludes_sensitive_fields(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    member = _register_member(client, admin_token, auth_header)
    client.patch(f"/api/elderly/{member['id']}", json={
        "vulnerability_notes": "Highly sensitive safeguarding note",
        "health_notes": "Highly sensitive health note",
        "dietary_requirements": "No nuts",
    }, headers=auth_header(admin_token))
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"], member=member)
    client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Started"}, headers=auth_header(vol_token))
    client.patch(
        f"/api/home-visits/{visit['id']}",
        json={"status": "Completed", "observations": "All good", "support_provided": "Groceries delivered"},
        headers=auth_header(vol_token),
    )

    resp = client.get(f"/api/volunteers/me/elderly-members/{member['id']}", headers=auth_header(vol_token))
    assert resp.status_code == 200
    body = resp.get_json()["elderly_member"]
    assert body["dietary_requirements"] == "No nuts"
    assert "vulnerability_notes" not in body
    assert "health_notes" not in body
    assert body["recent_visit"]["observations"] == "All good"


def test_elderly_member_snapshot_404s_for_unassigned_idor(client, make_user, make_staff_user, auth_header):
    """CRITICAL per spec: a volunteer must not be able to view a member's
    snapshot by guessing/incrementing an ID that isn't assigned to them."""
    _, admin_token = make_staff_user("admin")
    vol_a, _, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="ia@example.com", name="IA")
    _, vol_b_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="ib@example.com", name="IB")
    visit = _make_visit(client, admin_token, auth_header, vol_a["id"])
    member_id = visit["elderly_member_id"]

    resp = client.get(f"/api/volunteers/me/elderly-members/{member_id}", headers=auth_header(vol_b_token))
    assert resp.status_code == 404


def test_elderly_members_endpoints_forbidden_for_non_volunteer_role(client, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    resp = client.get("/api/volunteers/me/elderly-members", headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_elderly_access_revoked_immediately_after_rejection(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token, vid = _verified_volunteer(client, make_user, auth_header, admin_token, email="rej@example.com", name="Rej")
    _make_visit(client, admin_token, auth_header, vol_user["id"])
    assert client.get("/api/volunteers/me/elderly-members", headers=auth_header(vol_token)).status_code == 200

    client.patch(f"/api/volunteers/{vid}", json={"status": "Rejected"}, headers=auth_header(admin_token))
    resp = client.get("/api/volunteers/me/elderly-members", headers=auth_header(vol_token))
    assert resp.status_code == 403


# ---------- Report a Concern (volunteer-restricted Incident create) ----------

def test_verified_volunteer_can_report_a_concern(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.post("/api/incidents", json={
        "incident_type": "Welfare Concern", "severity": "Medium", "description": "Noticed low mood on visit",
    }, headers=auth_header(vol_token))
    assert resp.status_code == 201
    body = resp.get_json()["incident"]
    assert body["status"] == "Open"
    assert body["elderly_member_id"] is None


def test_unverified_volunteer_cannot_report_a_concern(client, make_user, auth_header):
    _, access_token, _ = make_user(email="pending@example.com")
    resp = client.post("/api/incidents", json={
        "incident_type": "Other", "severity": "Low", "description": "test",
    }, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_volunteer_cannot_set_privileged_incident_fields(client, make_user, make_staff_user, auth_header):
    """A volunteer trying to sneak status/resolution_notes into their
    concern report gets rejected outright, not silently ignored-and-applied."""
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.post("/api/incidents", json={
        "incident_type": "Other", "severity": "Low", "description": "test",
        "status": "Closed", "resolution_notes": "self-resolved",
    }, headers=auth_header(vol_token))
    assert resp.status_code == 400


def test_volunteer_cannot_list_or_view_incidents(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    created = client.post("/api/incidents", json={
        "incident_type": "Other", "severity": "Low", "description": "test",
    }, headers=auth_header(vol_token)).get_json()["incident"]

    assert client.get("/api/incidents", headers=auth_header(vol_token)).status_code == 403
    assert client.get(f"/api/incidents/{created['id']}", headers=auth_header(vol_token)).status_code == 403


def test_critical_concern_notifies_admin_and_staff(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin", email="admin2@example.com")
    _, staff_token = make_staff_user("staff", email="staff2@example.com")
    _, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.post("/api/incidents", json={
        "incident_type": "Emergency", "severity": "Critical", "description": "Needs urgent attention",
    }, headers=auth_header(vol_token))
    assert resp.status_code == 201

    admin_notifs = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"]
    staff_notifs = client.get("/api/notifications", headers=auth_header(staff_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Critical Incident" for n in admin_notifs)
    assert any(n["notification_type"] == "Critical Incident" for n in staff_notifs)


def test_concern_about_a_specific_elderly_member(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    member = _register_member(client, admin_token, auth_header)
    _make_visit(client, admin_token, auth_header, vol_user["id"], member=member)

    resp = client.post("/api/incidents", json={
        "elderly_member_id": member["id"], "incident_type": "Medical Concern", "severity": "High",
        "description": "Seemed unwell",
    }, headers=auth_header(vol_token))
    assert resp.status_code == 201
    assert resp.get_json()["incident"]["elderly_member_id"] == member["id"]


def test_admin_incident_flow_unchanged(client, make_staff_user, auth_header):
    """Regression: the pre-existing admin/staff incident-create path
    (full schema, required elderly_member_id, client-settable status)
    still works exactly as before."""
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    resp = client.post("/api/incidents", json={
        "elderly_member_id": member["id"], "incident_type": "Fall", "severity": "Medium",
        "occurred_at": "2026-01-01T10:00:00Z", "description": "Fell in the hallway",
        "emergency_contact_notified": True, "follow_up_required": False, "status": "Open",
    }, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["incident"]["elderly_member_id"] == member["id"]
