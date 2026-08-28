def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def test_staff_can_record_observation(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/health-records", json={
        "elderly_member_id": member["id"], "blood_pressure_systolic": 130, "blood_pressure_diastolic": 85,
        "pulse_bpm": 72, "wellbeing": "Good", "mood": "Cheerful",
    }, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["record"]
    assert body["elderly_member_name"] == "Mary Achieng"
    assert body["blood_pressure_systolic"] == 130
    assert body["follow_up_required"] is False


def test_volunteer_cannot_record_observation(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("admin")
    member = _register_member(client, staff_token, auth_header)
    _, access_token, _ = make_user()

    resp = client.post("/api/health-records", json={"elderly_member_id": member["id"]}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_record_rejects_unknown_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/health-records", json={"elderly_member_id": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_record_rejects_invalid_wellbeing(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/health-records", json={"elderly_member_id": member["id"], "wellbeing": "Excellent"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_record_rejects_out_of_range_vitals(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/health-records", json={"elderly_member_id": member["id"], "pulse_bpm": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_follow_up_flag_persists_across_partial_edit(client, make_staff_user, auth_header):
    """Regression: PATCHing without follow_up_required must not reset it to False."""
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    record = client.post("/api/health-records", json={
        "elderly_member_id": member["id"], "follow_up_required": True, "follow_up_notes": "See clinic next week",
    }, headers=auth_header(token)).get_json()["record"]
    assert record["follow_up_required"] is True

    patched = client.patch(f"/api/health-records/{record['id']}", json={"mood": "Tired"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["record"]["follow_up_required"] is True
    assert patched.get_json()["record"]["follow_up_notes"] == "See clinic next week"


def test_recorded_at_persists_across_partial_edit(client, make_staff_user, auth_header):
    """Regression: PATCHing without recorded_at must not null out a NOT NULL column."""
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    record = client.post("/api/health-records", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["record"]
    original_recorded_at = record["recorded_at"]

    patched = client.patch(f"/api/health-records/{record['id']}", json={"mood": "Calm"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["record"]["recorded_at"] == original_recorded_at


def test_list_filters_by_member_and_follow_up(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _register_member(client, token, auth_header, "Mary Achieng")
    m2 = _register_member(client, token, auth_header, "John Otieno")
    client.post("/api/health-records", json={"elderly_member_id": m1["id"], "follow_up_required": True}, headers=auth_header(token))
    client.post("/api/health-records", json={"elderly_member_id": m2["id"], "follow_up_required": False}, headers=auth_header(token))

    by_member = client.get(f"/api/health-records?elderly_member_id={m1['id']}", headers=auth_header(token))
    assert len(by_member.get_json()["records"]) == 1

    follow_up = client.get("/api/health-records?follow_up_required=true", headers=auth_header(token))
    names = [r["elderly_member_name"] for r in follow_up.get_json()["records"]]
    assert names == ["Mary Achieng"]


def test_admin_can_delete_record(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    record = client.post("/api/health-records", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["record"]
    resp = client.delete(f"/api/health-records/{record['id']}", headers=auth_header(token))
    assert resp.status_code == 204


def test_staff_cannot_delete_record(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)
    record = client.post("/api/health-records", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["record"]
    resp = client.delete(f"/api/health-records/{record['id']}", headers=auth_header(token))
    assert resp.status_code == 403
