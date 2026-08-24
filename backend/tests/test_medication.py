import datetime


def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


VALID = {"name": "Amlodipine", "dosage": "5mg", "schedule": "Once daily"}


def test_staff_can_prescribe_medication(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)

    resp = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["medication"]
    assert body["name"] == "Amlodipine"
    assert body["status"] == "Active"
    assert body["start_date"] == datetime.date.today().isoformat()


def test_volunteer_cannot_prescribe_medication(client, make_user, make_staff_user, auth_header):
    _, staff_token = make_staff_user("admin")
    member = _register_member(client, staff_token, auth_header)
    _, access_token, _ = make_user()

    resp = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_medication_rejects_unknown_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/medications", json={**VALID, "elderly_member_id": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_medication_rejects_missing_name(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    resp = client.post("/api/medications", json={"elderly_member_id": member["id"]}, headers=auth_header(token))
    assert resp.status_code == 400


def test_status_persists_across_partial_edit(client, make_staff_user, auth_header):
    """Regression: PATCHing without status must not reset it back to Active."""
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    med = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["medication"]

    discontinued = client.patch(f"/api/medications/{med['id']}", json={"status": "Discontinued"}, headers=auth_header(token))
    assert discontinued.get_json()["medication"]["status"] == "Discontinued"

    patched = client.patch(f"/api/medications/{med['id']}", json={"dosage": "10mg"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["medication"]["status"] == "Discontinued"
    assert patched.get_json()["medication"]["dosage"] == "10mg"


def test_list_filters_by_member_and_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    m1 = _register_member(client, token, auth_header, "Mary Achieng")
    m2 = _register_member(client, token, auth_header, "John Otieno")
    client.post("/api/medications", json={**VALID, "elderly_member_id": m1["id"]}, headers=auth_header(token))
    med2 = client.post("/api/medications", json={**VALID, "elderly_member_id": m2["id"]}, headers=auth_header(token)).get_json()["medication"]
    client.patch(f"/api/medications/{med2['id']}", json={"status": "Completed"}, headers=auth_header(token))

    by_member = client.get(f"/api/medications?elderly_member_id={m1['id']}", headers=auth_header(token))
    assert len(by_member.get_json()["medications"]) == 1

    active = client.get("/api/medications?status=Active", headers=auth_header(token))
    names = [m["elderly_member_name"] for m in active.get_json()["medications"]]
    assert names == ["Mary Achieng"]


# ---------- Administration log ----------

def test_log_administration(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    med = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["medication"]

    resp = client.post(f"/api/medications/{med['id']}/administrations", json={"status": "Given"}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["administration"]["status"] == "Given"

    listed = client.get(f"/api/medications/{med['id']}/administrations", headers=auth_header(token))
    assert len(listed.get_json()["administrations"]) == 1


def test_administration_defaults_to_given(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    med = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["medication"]

    resp = client.post(f"/api/medications/{med['id']}/administrations", json={}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["administration"]["status"] == "Given"


def test_administration_rejects_invalid_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    med = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["medication"]

    resp = client.post(f"/api/medications/{med['id']}/administrations", json={"status": "Unknown"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_administration_rejects_unknown_medication(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/medications/999/administrations", json={}, headers=auth_header(token))
    assert resp.status_code == 404


# ---------- Delete ----------

def test_admin_can_delete_medication_with_no_history(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    med = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["medication"]

    resp = client.delete(f"/api/medications/{med['id']}", headers=auth_header(token))
    assert resp.status_code == 204


def test_cannot_delete_medication_with_administration_history(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _register_member(client, token, auth_header)
    med = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["medication"]
    client.post(f"/api/medications/{med['id']}/administrations", json={"status": "Given"}, headers=auth_header(token))

    resp = client.delete(f"/api/medications/{med['id']}", headers=auth_header(token))
    assert resp.status_code == 409


def test_staff_cannot_delete_medication(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = _register_member(client, token, auth_header)
    med = client.post("/api/medications", json={**VALID, "elderly_member_id": member["id"]}, headers=auth_header(token)).get_json()["medication"]
    resp = client.delete(f"/api/medications/{med['id']}", headers=auth_header(token))
    assert resp.status_code == 403
