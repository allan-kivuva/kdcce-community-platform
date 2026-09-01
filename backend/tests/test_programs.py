VALID_PROGRAM = {"name": "Feeding Program", "category": "Nutrition", "status": "Active"}


def test_admin_can_create_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["program"]
    assert body["name"] == "Feeding Program"
    assert body["activity_count"] == 0
    assert body["active"] is True


def test_staff_can_create_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token))
    assert resp.status_code == 201


def test_volunteer_cannot_create_program(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_programs(client):
    assert client.get("/api/programs").status_code == 401


def test_create_defaults_to_draft_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/programs", json={"name": "New Initiative"}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["program"]["status"] == "Draft"


def test_create_rejects_invalid_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/programs", json={**VALID_PROGRAM, "status": "Cancelled"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_coordinator_must_be_staff_or_admin(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol, _, _ = make_user(email="notcoord@example.com")
    resp = client.post("/api/programs", json={**VALID_PROGRAM, "coordinator_id": vol["id"]}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_coordinator_can_be_staff(client, make_staff_user, auth_header):
    admin, admin_token = make_staff_user("admin")
    staff, _ = make_staff_user("staff", email="coordinator@example.com")
    resp = client.post("/api/programs", json={**VALID_PROGRAM, "coordinator_id": staff["id"]}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["program"]["coordinator"] == "Staffer"


# ---------- Draft/inactive visibility ----------

def test_volunteer_only_sees_active_programs(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    client.post("/api/programs", json={"name": "Active One", "status": "Active"}, headers=auth_header(admin_token))
    client.post("/api/programs", json={"name": "Still Drafting", "status": "Draft"}, headers=auth_header(admin_token))
    _, vol_token, _ = make_user(email="progviewer@example.com")

    resp = client.get("/api/programs", headers=auth_header(vol_token))
    names = [p["name"] for p in resp.get_json()["programs"]]
    assert "Active One" in names
    assert "Still Drafting" not in names


def test_admin_sees_all_program_statuses(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    client.post("/api/programs", json={"name": "Archived One", "status": "Archived"}, headers=auth_header(admin_token))

    resp = client.get("/api/programs", headers=auth_header(admin_token))
    names = [p["name"] for p in resp.get_json()["programs"]]
    assert "Archived One" in names


def test_volunteer_cannot_view_draft_program_by_id(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/programs", json={"name": "Hidden Draft", "status": "Draft"}, headers=auth_header(admin_token)).get_json()["program"]
    _, vol_token, _ = make_user(email="nodraftpeek@example.com")

    resp = client.get(f"/api/programs/{created['id']}", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_volunteer_can_view_active_program_by_id(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(admin_token)).get_json()["program"]
    _, vol_token, _ = make_user(email="canview@example.com")

    resp = client.get(f"/api/programs/{created['id']}", headers=auth_header(vol_token))
    assert resp.status_code == 200


# ---------- Edit ----------

def test_admin_can_edit_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token)).get_json()["program"]
    resp = client.patch(f"/api/programs/{created['id']}", json={"status": "Paused"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["program"]["status"] == "Paused"


def test_volunteer_cannot_edit_program(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(admin_token)).get_json()["program"]
    _, vol_token, _ = make_user(email="noeditprog@example.com")
    resp = client.patch(f"/api/programs/{created['id']}", json={"status": "Archived"}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_slug_must_be_unique(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/programs", json={**VALID_PROGRAM, "slug": "feeding"}, headers=auth_header(token))
    resp = client.post("/api/programs", json={"name": "Another", "slug": "feeding"}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Activity linking ----------

def test_activity_can_link_to_a_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token)).get_json()["program"]
    resp = client.post("/api/activities", json={
        "title": "Meal Prep", "activity_type": "Community Event", "scheduled_at": "2027-01-15T09:00:00+00:00",
        "program_id": program["id"],
    }, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["activity"]["program_id"] == program["id"]
    assert resp.get_json()["activity"]["program_name"] == "Feeding Program"


def test_activity_without_program_still_valid(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/activities", json={"title": "Standalone", "activity_type": "Social", "scheduled_at": "2027-01-15T09:00:00+00:00"}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["activity"]["program_id"] is None


def test_activity_rejects_unknown_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/activities", json={"title": "Bad Link", "activity_type": "Social", "scheduled_at": "2027-01-15T09:00:00+00:00", "program_id": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_activity_can_be_reassigned_between_programs(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    p1 = client.post("/api/programs", json={"name": "P1", "status": "Active"}, headers=auth_header(token)).get_json()["program"]
    p2 = client.post("/api/programs", json={"name": "P2", "status": "Active"}, headers=auth_header(token)).get_json()["program"]
    activity = client.post("/api/activities", json={"title": "Movable", "activity_type": "Social", "scheduled_at": "2027-01-15T09:00:00+00:00", "program_id": p1["id"]}, headers=auth_header(token)).get_json()["activity"]

    resp = client.patch(f"/api/activities/{activity['id']}", json={"program_id": p2["id"]}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["activity"]["program_id"] == p2["id"]


def test_activities_list_filterable_by_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token)).get_json()["program"]
    client.post("/api/activities", json={"title": "In program", "activity_type": "Social", "scheduled_at": "2027-01-15T09:00:00+00:00", "program_id": program["id"]}, headers=auth_header(token))
    client.post("/api/activities", json={"title": "Not in program", "activity_type": "Social", "scheduled_at": "2027-01-15T09:00:00+00:00"}, headers=auth_header(token))

    resp = client.get(f"/api/programs/{program['id']}", headers=auth_header(token))
    assert resp.get_json()["program"]["activity_count"] == 1

    resp = client.get(f"/api/activities?program_id={program['id']}", headers=auth_header(token))
    titles = [a["title"] for a in resp.get_json()["activities"]]
    assert titles == ["In program"]


# ---------- Analytics ----------

def test_analytics_is_admin_staff_only(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    program = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(admin_token)).get_json()["program"]
    _, vol_token, _ = make_user(email="noanalytics@example.com")
    resp = client.get(f"/api/programs/{program['id']}/analytics", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_analytics_with_no_activities_returns_zeros(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token)).get_json()["program"]
    resp = client.get(f"/api/programs/{program['id']}/analytics", headers=auth_header(token))
    assert resp.status_code == 200
    analytics = resp.get_json()["analytics"]
    assert analytics == {
        "activities_count": 0, "upcoming_activities": 0, "completed_activities": 0,
        "elderly_participants_served": 0, "repeat_participants": 0, "total_event_attendance": 0,
        "volunteer_participation": 0, "attendance_rate": None,
    }


def test_analytics_counts_real_participation_without_double_counting(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token)).get_json()["program"]

    a1 = client.post("/api/activities", json={"title": "Session 1", "activity_type": "Social", "scheduled_at": "2027-01-15T09:00:00+00:00", "status": "Completed", "program_id": program["id"]}, headers=auth_header(token)).get_json()["activity"]
    a2 = client.post("/api/activities", json={"title": "Session 2", "activity_type": "Social", "scheduled_at": "2027-02-15T09:00:00+00:00", "program_id": program["id"]}, headers=auth_header(token)).get_json()["activity"]

    member = client.post("/api/elderly", json={"full_name": "Repeat Member", "gender": "Female"}, headers=auth_header(token)).get_json()["member"]
    other_member = client.post("/api/elderly", json={"full_name": "One-time Member", "gender": "Male"}, headers=auth_header(token)).get_json()["member"]

    client.post(f"/api/activities/{a1['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    p1 = client.get(f"/api/activities/{a1['id']}/participants", headers=auth_header(token)).get_json()["participants"][0]
    client.patch(f"/api/activities/{a1['id']}/participants/{p1['id']}", json={"status": "Attended"}, headers=auth_header(token))

    client.post(f"/api/activities/{a1['id']}/participants", json={"elderly_member_id": other_member["id"]}, headers=auth_header(token))
    p2 = client.get(f"/api/activities/{a1['id']}/participants", headers=auth_header(token)).get_json()["participants"]
    p2 = next(p for p in p2 if p["elderly_member_id"] == other_member["id"])
    client.patch(f"/api/activities/{a1['id']}/participants/{p2['id']}", json={"status": "No-show"}, headers=auth_header(token))

    client.post(f"/api/activities/{a2['id']}/participants", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    resp = client.get(f"/api/programs/{program['id']}/analytics", headers=auth_header(token))
    analytics = resp.get_json()["analytics"]
    assert analytics["activities_count"] == 2
    assert analytics["completed_activities"] == 1
    assert analytics["elderly_participants_served"] == 2
    assert analytics["repeat_participants"] == 1
    assert analytics["total_event_attendance"] == 1
    assert analytics["attendance_rate"] == 50


def test_analytics_excludes_activities_from_other_programs(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json=VALID_PROGRAM, headers=auth_header(token)).get_json()["program"]
    other_program = client.post("/api/programs", json={"name": "Unrelated"}, headers=auth_header(token)).get_json()["program"]
    client.post("/api/activities", json={"title": "In other program", "activity_type": "Social", "scheduled_at": "2027-01-15T09:00:00+00:00", "program_id": other_program["id"]}, headers=auth_header(token))

    resp = client.get(f"/api/programs/{program['id']}/analytics", headers=auth_header(token))
    assert resp.get_json()["analytics"]["activities_count"] == 0
