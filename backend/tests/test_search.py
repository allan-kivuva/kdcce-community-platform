def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def test_admin_can_search_elderly_members(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    _register_member(client, token, auth_header, "Mary Akinyi")
    _register_member(client, token, auth_header, "John Otieno")

    resp = client.get("/api/search?q=Akinyi", headers=auth_header(token))
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert len(results["elderly_members"]) == 1
    assert results["elderly_members"][0]["full_name"] == "Mary Akinyi"


def test_search_covers_home_visits_and_assistance_and_follow_ups(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header, "Peter Otieno")
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "x"}, headers=auth_header(token))
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Companionship", "description": "x"}, headers=auth_header(token))
    client.post("/api/followups", json={"elderly_member_id": member["id"], "reason": "Hospital appointment"}, headers=auth_header(token))

    results = client.get("/api/search?q=Otieno", headers=auth_header(token)).get_json()["results"]
    assert len(results["home_visits"]) == 1
    assert len(results["assistance_requests"]) == 1
    assert len(results["follow_ups"]) == 1


def test_search_requires_at_least_two_characters(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/search?q=a", headers=auth_header(token))
    assert resp.status_code == 400


def test_volunteer_cannot_search(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.get("/api/search?q=Mary", headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_search(client):
    assert client.get("/api/search?q=Mary").status_code == 401
