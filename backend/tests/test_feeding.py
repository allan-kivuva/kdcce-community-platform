import datetime


def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def test_staff_can_plan_a_meal(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/meals", json={"meal_type": "Lunch", "description": "Ugali, sukuma wiki, beans"}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["meal"]
    assert body["meal_type"] == "Lunch"
    assert body["meal_date"] == datetime.date.today().isoformat()
    assert body["attendee_count"] == 0


def test_volunteer_cannot_plan_a_meal(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_meal_rejects_invalid_type(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/meals", json={"meal_type": "Brunch"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_meal_accepts_explicit_date(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/meals", json={"meal_type": "Breakfast", "meal_date": "2026-01-15"}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["meal"]["meal_date"] == "2026-01-15"


def test_list_meals_filters_by_date_and_type(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/meals", json={"meal_type": "Breakfast", "meal_date": "2026-01-15"}, headers=auth_header(token))
    client.post("/api/meals", json={"meal_type": "Lunch", "meal_date": "2026-01-16"}, headers=auth_header(token))

    by_date = client.get("/api/meals?date=2026-01-15", headers=auth_header(token))
    assert len(by_date.get_json()["meals"]) == 1

    by_type = client.get("/api/meals?meal_type=Lunch", headers=auth_header(token))
    assert len(by_type.get_json()["meals"]) == 1
    assert by_type.get_json()["meals"][0]["meal_type"] == "Lunch"


def test_list_meals_rejects_bad_date_format(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/meals?date=not-a-date", headers=auth_header(token))
    assert resp.status_code == 400


def test_meal_date_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    meal = client.post("/api/meals", json={"meal_type": "Lunch", "meal_date": "2026-01-15"}, headers=auth_header(token)).get_json()["meal"]
    patched = client.patch(f"/api/meals/{meal['id']}", json={"description": "Updated menu"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["meal"]["meal_date"] == "2026-01-15"
    assert patched.get_json()["meal"]["description"] == "Updated menu"


# ---------- Attendance ----------

def test_staff_can_mark_meal_attendance(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]

    resp = client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["attendance"]["elderly_member_name"] == "Mary Achieng"

    updated_meal = client.get(f"/api/meals/{meal['id']}", headers=auth_header(token)).get_json()["meal"]
    assert updated_meal["attendee_count"] == 1


def test_cannot_mark_same_member_twice_for_same_meal(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    resp = client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 409


def test_attendance_rejects_unknown_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    resp = client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_attendance_rejects_unknown_meal(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/meals/999/attendance", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 404


def test_volunteer_cannot_mark_attendance(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(admin_token)).get_json()["meal"]
    _, access_token, _ = make_user()

    resp = client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": member["id"]}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_list_attendance_for_a_meal(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _register_member(client, token, auth_header, "Mary Achieng")
    m2 = _register_member(client, token, auth_header, "John Otieno")
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": m1["id"]}, headers=auth_header(token))
    client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": m2["id"]}, headers=auth_header(token))

    resp = client.get(f"/api/meals/{meal['id']}/attendance", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.get_json()["attendance"]) == 2


# ---------- Delete ----------

def test_admin_can_delete_meal_with_no_attendance(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    resp = client.delete(f"/api/meals/{meal['id']}", headers=auth_header(token))
    assert resp.status_code == 204


def test_cannot_delete_meal_with_recorded_attendance(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    client.post(f"/api/meals/{meal['id']}/attendance", json={"elderly_member_id": member["id"]}, headers=auth_header(token))

    resp = client.delete(f"/api/meals/{meal['id']}", headers=auth_header(token))
    assert resp.status_code == 409


def test_staff_cannot_delete_meal(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    meal = client.post("/api/meals", json={"meal_type": "Lunch"}, headers=auth_header(token)).get_json()["meal"]
    resp = client.delete(f"/api/meals/{meal['id']}", headers=auth_header(token))
    assert resp.status_code == 403
