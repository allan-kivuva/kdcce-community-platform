VALID_COURSE = {"title": "Safeguarding Basics", "description": "Intro to safeguarding practice", "estimated_minutes": 30, "required": True}


def _verified_volunteer(client, make_user, auth_header, admin_token, email="train-vol@example.com"):
    user, access_token, _ = make_user(email=email, name="Training Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


# ---------- Course CRUD permissions ----------

def test_admin_can_create_course(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/training", json=VALID_COURSE, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["course"]["required"] is True


def test_staff_can_create_course(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/training", json=VALID_COURSE, headers=auth_header(token))
    assert resp.status_code == 201


def test_volunteer_cannot_create_course(client, make_user, auth_header):
    _, token, _ = make_user(email="nocreatecourse@example.com")
    resp = client.post("/api/training", json=VALID_COURSE, headers=auth_header(token))
    assert resp.status_code == 403


def test_admin_can_edit_and_deactivate_course(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(token)).get_json()["course"]["id"]

    resp = client.patch(f"/api/training/{course_id}", json={"active": False}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["course"]["active"] is False


def test_creating_and_editing_a_course_is_audited(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    course = client.post("/api/training", json=VALID_COURSE, headers=auth_header(token)).get_json()["course"]
    client.patch(f"/api/training/{course['id']}", json={"active": False}, headers=auth_header(token))

    logs_resp = client.get(
        f"/api/audit-logs?resource_type=training_course&resource_id={course['id']}", headers=auth_header(token)
    )
    logs = logs_resp.get_json()["audit_logs"]
    assert len(logs) == 2
    actions = {l["action"] for l in logs}
    assert actions == {"create", "update"}
    create_log = next(l for l in logs if l["action"] == "create")
    assert create_log["after"]["title"] == "Safeguarding Basics"
    update_log = next(l for l in logs if l["action"] == "update")
    assert update_log["before"]["active"] is True
    assert update_log["after"]["active"] is False
    for log in logs:
        for snapshot in (log["before"], log["after"]):
            if snapshot is None:
                continue
            for key in snapshot:
                assert "password" not in key.lower()
                assert "token" not in key.lower()


def test_volunteer_cannot_edit_course(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    _, token, _ = make_user(email="noeditcourse@example.com")
    resp = client.patch(f"/api/training/{course_id}", json={"active": False}, headers=auth_header(token))
    assert resp.status_code == 403


def test_inactive_courses_hidden_from_volunteer_list_by_default(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    client.patch(f"/api/training/{course_id}", json={"active": False}, headers=auth_header(admin_token))

    _, vol_token, _ = make_user(email="hiddencourse@example.com")
    courses = client.get("/api/training", headers=auth_header(vol_token)).get_json()["courses"]
    assert all(c["id"] != course_id for c in courses)


def test_admin_can_see_inactive_courses_with_flag(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    client.patch(f"/api/training/{course_id}", json={"active": False}, headers=auth_header(admin_token))

    courses = client.get("/api/training?include_inactive=true", headers=auth_header(admin_token)).get_json()["courses"]
    assert any(c["id"] == course_id for c in courses)


def test_unauthenticated_cannot_list_training(client):
    assert client.get("/api/training").status_code == 401


# ---------- Volunteer progress ----------

def test_volunteer_sees_not_started_by_default(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token))
    _, vol_token, _ = make_user(email="notstarted@example.com")

    courses = client.get("/api/training/me/progress", headers=auth_header(vol_token)).get_json()["courses"]
    assert courses[0]["progress"]["status"] == "Not Started"


def test_volunteer_can_mark_in_progress_then_completed(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    _, vol_token, _ = make_user(email="progressflow@example.com")

    resp = client.patch(f"/api/training/me/progress/{course_id}", json={"status": "In Progress"}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["progress"]["started_at"] is not None
    assert resp.get_json()["progress"]["completed_at"] is None

    resp = client.patch(f"/api/training/me/progress/{course_id}", json={"status": "Completed"}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["progress"]["completed_at"] is not None


def test_progress_cannot_be_reset_to_not_started(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    _, vol_token, _ = make_user(email="noreset@example.com")
    resp = client.patch(f"/api/training/me/progress/{course_id}", json={"status": "Not Started"}, headers=auth_header(vol_token))
    assert resp.status_code == 400


def test_volunteer_cannot_modify_another_volunteers_progress(client, make_user, make_staff_user, auth_header):
    """There is no endpoint that even takes another volunteer's id for
    progress — /me/progress/<course_id> is always scoped to the caller's
    own profile — so this is really confirming volunteer B's update never
    shows up on volunteer A's own progress view."""
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    _, token_a, _ = make_user(email="progress-a@example.com")
    _, token_b, _ = make_user(email="progress-b@example.com")

    client.patch(f"/api/training/me/progress/{course_id}", json={"status": "Completed"}, headers=auth_header(token_b))

    courses_a = client.get("/api/training/me/progress", headers=auth_header(token_a)).get_json()["courses"]
    assert courses_a[0]["progress"]["status"] == "Not Started"


def test_completing_a_course_triggers_the_training_complete_achievement(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    _, vol_token, _ = make_user(email="trainingachievement@example.com")

    client.patch(f"/api/training/me/progress/{course_id}", json={"status": "Completed"}, headers=auth_header(vol_token))

    achievements = client.get("/api/volunteers/me/achievements", headers=auth_header(vol_token)).get_json()["achievements"]
    codes = [e["achievement"]["code"] for e in achievements["earned"]]
    assert "training_complete" in codes


def test_staff_can_view_course_completions(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    _, vol_token, _ = make_user(email="completionsview@example.com", name="Completions Volunteer")
    client.patch(f"/api/training/me/progress/{course_id}", json={"status": "Completed"}, headers=auth_header(vol_token))

    resp = client.get(f"/api/training/{course_id}/completions", headers=auth_header(admin_token))
    assert resp.status_code == 200
    completions = resp.get_json()["completions"]
    assert len(completions) == 1
    assert completions[0]["status"] == "Completed"
    assert completions[0]["volunteer_name"] == "Completions Volunteer"


def test_volunteer_cannot_view_course_completions(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    _, vol_token, _ = make_user(email="nocompletionsview@example.com")
    resp = client.get(f"/api/training/{course_id}/completions", headers=auth_header(vol_token))
    assert resp.status_code == 403


# ---------- Admin/staff view of one volunteer's training ----------

def test_admin_can_view_a_volunteers_training_progress(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    course_id = client.post("/api/training", json=VALID_COURSE, headers=auth_header(admin_token)).get_json()["course"]["id"]
    user, vol_token, _ = make_user(email="admintrainview@example.com")
    client.patch(f"/api/training/me/progress/{course_id}", json={"status": "Completed"}, headers=auth_header(vol_token))
    vid = next(v for v in client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"] if v["email"] == "admintrainview@example.com")["id"]

    resp = client.get(f"/api/volunteers/{vid}/training", headers=auth_header(admin_token))
    assert resp.status_code == 200
    courses = resp.get_json()["courses"]
    assert courses[0]["progress"]["status"] == "Completed"


def test_volunteer_cannot_view_training_via_the_admin_route(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    user, _, _ = make_user(email="notrainpeek@example.com")
    vid = next(v for v in client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"] if v["email"] == "notrainpeek@example.com")["id"]
    _, other_token, _ = make_user(email="nosytrain@example.com")
    resp = client.get(f"/api/volunteers/{vid}/training", headers=auth_header(other_token))
    assert resp.status_code == 403
