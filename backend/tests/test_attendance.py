def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def test_staff_can_check_in_a_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["attendance"]
    assert body["elderly_member_name"] == "Mary Achieng"
    assert body["check_out_at"] is None


def test_volunteer_cannot_check_in_a_member(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("admin")
    member = _register_member(client, staff_token, auth_header)
    _, access_token, _ = make_user()

    resp = client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_check_in_rejects_unknown_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/attendance/check-in", json={"elderly_member_id": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_cannot_check_in_twice_same_day_without_checkout(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)

    first = client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert first.status_code == 201
    second = client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert second.status_code == 409


def test_check_out_flow(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    record = client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["attendance"]

    resp = client.patch(f"/api/attendance/{record['id']}/check-out", json={}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["attendance"]["check_out_at"] is not None


def test_double_check_out_rejected(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    record = client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["attendance"]

    client.patch(f"/api/attendance/{record['id']}/check-out", json={}, headers=auth_header(token))
    second = client.patch(f"/api/attendance/{record['id']}/check-out", json={}, headers=auth_header(token))
    assert second.status_code == 409


def test_can_check_in_again_after_checkout(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    record = client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["attendance"]
    client.patch(f"/api/attendance/{record['id']}/check-out", json={}, headers=auth_header(token))

    resp = client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 201


def test_list_attendance_filters_by_date(client, make_staff_user, auth_header):
    import datetime
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    client.post("/api/attendance/check-in", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    today = datetime.date.today().isoformat()
    resp = client.get(f"/api/attendance?date={today}", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.get_json()["attendance"]) == 1

    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    empty = client.get(f"/api/attendance?date={tomorrow}", headers=auth_header(token))
    assert empty.get_json()["attendance"] == []


def test_list_attendance_rejects_bad_date_format(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/attendance?date=not-a-date", headers=auth_header(token))
    assert resp.status_code == 400
