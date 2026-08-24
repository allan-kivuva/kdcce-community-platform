def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def test_timeline_empty_for_member_with_no_history(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)

    resp = client.get(f"/api/elderly/{member['id']}/timeline", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["timeline"] == []
    assert body["pagination"]["total"] == 0
    assert body["member"]["id"] == member["id"]


def test_timeline_combines_every_source_module(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    mid = member["id"]

    client.post("/api/attendance/check-in", json={"elderly_member_id": mid}, headers=auth_header(token))
    client.post("/api/health-records", json={"elderly_member_id": mid, "mood": "Good"}, headers=auth_header(token))
    med = client.post("/api/medications", json={"elderly_member_id": mid, "name": "Medication A"}, headers=auth_header(token)).get_json()["medication"]
    client.post(f"/api/medications/{med['id']}/administrations", json={"status": "Given"}, headers=auth_header(token))
    client.post("/api/home-visits", json={"elderly_member_id": mid, "reason": "Routine check"}, headers=auth_header(token))
    client.post("/api/assistance-requests", json={"elderly_member_id": mid, "request_type": "Companionship", "description": "Weekly visitor"}, headers=auth_header(token))
    client.post("/api/incidents", json={"elderly_member_id": mid, "incident_type": "Fall", "description": "Slipped"}, headers=auth_header(token))
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": mid}, headers=auth_header(token))

    resp = client.get(f"/api/elderly/{mid}/timeline", headers=auth_header(token))
    assert resp.status_code == 200
    types = {e["type"] for e in resp.get_json()["timeline"]}
    assert types == {"attendance", "health", "medication", "home_visit", "assistance", "incident", "meal"}
    assert resp.get_json()["pagination"]["total"] == 7


def test_timeline_sorted_newest_first_and_paginates(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    mid = member["id"]

    for i in range(3):
        client.post("/api/incidents", json={"elderly_member_id": mid, "incident_type": "Other", "description": f"Event {i}"}, headers=auth_header(token))

    resp = client.get(f"/api/elderly/{mid}/timeline?per_page=2", headers=auth_header(token))
    body = resp.get_json()
    assert len(body["timeline"]) == 2
    assert body["pagination"]["total"] == 3
    assert body["pagination"]["pages"] == 2
    # newest first
    assert body["timeline"][0]["details"]["description"] == "Event 2"


def test_timeline_home_visit_shows_photo_attached_flag(client, make_staff_user, auth_header):
    import io
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    mid = member["id"]
    visit = client.post("/api/home-visits", json={"elderly_member_id": mid, "reason": "Check"}, headers=auth_header(token)).get_json()["visit"]

    resp = client.get(f"/api/elderly/{mid}/timeline", headers=auth_header(token))
    assert resp.get_json()["timeline"][0]["details"]["has_photo"] is False

    client.post(
        f"/api/home-visits/{visit['id']}/photo",
        data={"photo": (io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 50), "a.jpg")},
        content_type="multipart/form-data",
        headers=auth_header(token),
    )
    resp = client.get(f"/api/elderly/{mid}/timeline", headers=auth_header(token))
    assert resp.get_json()["timeline"][0]["details"]["has_photo"] is True


def test_volunteer_cannot_access_timeline(client, make_user, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    _, vol_token, _ = make_user()

    resp = client.get(f"/api/elderly/{member['id']}/timeline", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_timeline(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.get(f"/api/elderly/{member['id']}/timeline")
    assert resp.status_code == 401
