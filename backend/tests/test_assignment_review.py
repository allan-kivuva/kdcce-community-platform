def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _completed_visit(client, admin_token, auth_header, assignee_id):
    member = _register_member(client, admin_token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": assignee_id}, headers=auth_header(admin_token)).get_json()["visit"]
    client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed"}, headers=auth_header(admin_token))
    return visit


# ---------- Creation, only-when-Completed, admin-only ----------

def test_admin_can_review_a_completed_visit(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 5, "comment": "Excellent visit, very thorough."}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    body = resp.get_json()["review"]
    assert body["rating"] == 5
    assert body["comment"] == "Excellent visit, very thorough."
    assert body["reviewed_by"] == "Staffer"


def test_staff_cannot_review_even_though_staff_can_manage_visits(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, staff_token = make_staff_user("staff", email="reviewer-staff@example.com")
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 4}, headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_volunteer_cannot_review_their_own_completed_visit(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 5}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_cannot_review_a_visit_that_is_not_completed(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    member = _register_member(client, admin_token, auth_header)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(admin_token)).get_json()["visit"]

    resp = client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 5}, headers=auth_header(admin_token))
    assert resp.status_code == 409


def test_rejects_rating_out_of_range(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])

    for bad_rating in (0, 6, -1):
        resp = client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": bad_rating}, headers=auth_header(admin_token))
        assert resp.status_code == 400


def test_comment_is_optional(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 3}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["review"]["comment"] is None


def test_resubmitting_a_review_replaces_it_not_duplicates(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])

    client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 2, "comment": "Needs improvement"}, headers=auth_header(admin_token))
    resp = client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 5, "comment": "Actually, great work"}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["review"]["rating"] == 5

    fetched = client.get(f"/api/home-visits/{visit['id']}/review", headers=auth_header(admin_token))
    assert fetched.get_json()["review"]["rating"] == 5
    assert fetched.get_json()["review"]["comment"] == "Actually, great work"


# ---------- Visibility ----------

def test_volunteer_can_see_review_of_their_own_completed_visit(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])
    client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 4, "comment": "Good work"}, headers=auth_header(admin_token))

    resp = client.get(f"/api/home-visits/{visit['id']}/review", headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["review"]["rating"] == 4


def test_other_volunteer_cannot_see_someone_elses_review(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="review-a@example.com")
    _, vol_b_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="review-b@example.com")
    visit = _completed_visit(client, admin_token, auth_header, vol_a["id"])
    client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 3}, headers=auth_header(admin_token))

    resp = client.get(f"/api/home-visits/{visit['id']}/review", headers=auth_header(vol_b_token))
    assert resp.status_code == 403


def test_no_review_yet_returns_404(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.get(f"/api/home-visits/{visit['id']}/review", headers=auth_header(admin_token))
    assert resp.status_code == 404


def test_unauthenticated_cannot_review_or_view(client):
    assert client.post("/api/home-visits/1/review", json={"rating": 5}).status_code == 401
    assert client.get("/api/home-visits/1/review").status_code == 401


# ---------- Notification ----------

def test_review_notifies_the_volunteer(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _completed_visit(client, admin_token, auth_header, vol_user["id"])

    client.post(f"/api/home-visits/{visit['id']}/review", json={"rating": 5, "comment": "Great job"}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications?notification_type=Assignment%20Reviewed", headers=auth_header(vol_token)).get_json()["notifications"]
    assert len(notifications) == 1
    assert "Great job" in notifications[0]["message"]
    assert "★★★★★" in notifications[0]["title"]


# ---------- Assistance requests: same mechanism, spot-checked ----------

def test_assistance_request_review_end_to_end(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    member = _register_member(client, admin_token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(admin_token)).get_json()["request"]
    client.patch(f"/api/assistance-requests/{req['id']}", json={"status": "Completed"}, headers=auth_header(admin_token))

    resp = client.post(f"/api/assistance-requests/{req['id']}/review", json={"rating": 4}, headers=auth_header(admin_token))
    assert resp.status_code == 201

    assert client.get(f"/api/assistance-requests/{req['id']}/review", headers=auth_header(vol_token)).status_code == 200
    assert client.post(f"/api/assistance-requests/{req['id']}/review", json={"rating": 3}, headers=auth_header(vol_token)).status_code == 403


def test_cannot_review_uncompleted_assistance_request(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, _ = _verified_volunteer(client, make_user, auth_header, admin_token)
    member = _register_member(client, admin_token, auth_header)
    req = client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "x", "assigned_to_id": vol_user["id"]}, headers=auth_header(admin_token)).get_json()["request"]

    resp = client.post(f"/api/assistance-requests/{req['id']}/review", json={"rating": 5}, headers=auth_header(admin_token))
    assert resp.status_code == 409
