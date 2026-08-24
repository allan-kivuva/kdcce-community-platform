import pytest


VALID_MEMBER = {"full_name": "Mary Achieng", "gender": "Female"}


# ---------- OPAs ----------

def test_admin_can_create_and_list_opas(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/opas", json={"name": "Kibera OPA", "location": "Kibera"}, headers=auth_header(token))
    assert resp.status_code == 201

    listed = client.get("/api/opas", headers=auth_header(token))
    assert listed.status_code == 200
    assert listed.get_json()["opas"][0]["name"] == "Kibera OPA"


def test_volunteer_cannot_access_opas(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.get("/api/opas", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_opas(client):
    resp = client.get("/api/opas")
    assert resp.status_code == 401


def test_opa_create_rejects_duplicate_name(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/opas", json={"name": "Kibera OPA"}, headers=auth_header(token))
    resp = client.post("/api/opas", json={"name": "Kibera OPA"}, headers=auth_header(token))
    assert resp.status_code == 409


def test_opa_update_and_delete(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    opa = client.post("/api/opas", json={"name": "Kibera OPA"}, headers=auth_header(token)).get_json()["opa"]

    patched = client.patch(f"/api/opas/{opa['id']}", json={"location": "Kibera, Nairobi"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["opa"]["location"] == "Kibera, Nairobi"

    deleted = client.delete(f"/api/opas/{opa['id']}", headers=auth_header(token))
    assert deleted.status_code == 204


def test_deleting_opa_clears_reference_on_its_members(client, make_staff_user, auth_header):
    """Regression: relies on SQLite FK enforcement actually being on —
    see extensions.py — otherwise ondelete='SET NULL' is silently ignored."""
    _, token = make_staff_user("admin")
    opa = client.post("/api/opas", json={"name": "Kibera OPA"}, headers=auth_header(token)).get_json()["opa"]
    member = client.post("/api/elderly", json={**VALID_MEMBER, "opa_id": opa["id"]}, headers=auth_header(token)).get_json()["member"]

    client.delete(f"/api/opas/{opa['id']}", headers=auth_header(token))

    refreshed = client.get(f"/api/elderly/{member['id']}", headers=auth_header(token)).get_json()["member"]
    assert refreshed["opa_id"] is None
    assert refreshed["opa_name"] is None


# ---------- Elderly members ----------

def test_admin_can_register_elderly_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/elderly", json=VALID_MEMBER, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["member"]
    assert body["full_name"] == "Mary Achieng"
    assert body["member_id"].startswith("KDCCE-")
    assert body["status"] == "Active"


def test_staff_can_register_elderly_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/elderly", json=VALID_MEMBER, headers=auth_header(token))
    assert resp.status_code == 201


def test_volunteer_cannot_access_elderly_members(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.get("/api/elderly", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_elderly_members(client):
    resp = client.get("/api/elderly")
    assert resp.status_code == 401


def test_elderly_create_rejects_missing_full_name(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/elderly", json={"gender": "Female"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_elderly_create_rejects_invalid_gender(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/elderly", json={"full_name": "X", "gender": "Unknown"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_elderly_create_rejects_unknown_opa(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/elderly", json={**VALID_MEMBER, "opa_id": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_elderly_create_links_valid_opa(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    opa = client.post("/api/opas", json={"name": "Kibera OPA"}, headers=auth_header(token)).get_json()["opa"]
    resp = client.post("/api/elderly", json={**VALID_MEMBER, "opa_id": opa["id"]}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["member"]["opa_name"] == "Kibera OPA"


def test_elderly_search_by_name_or_member_id(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/elderly", json={"full_name": "Mary Achieng", "gender": "Female"}, headers=auth_header(token))
    client.post("/api/elderly", json={"full_name": "John Otieno", "gender": "Male"}, headers=auth_header(token))

    resp = client.get("/api/elderly?q=mary", headers=auth_header(token))
    assert resp.status_code == 200
    names = [m["full_name"] for m in resp.get_json()["members"]]
    assert names == ["Mary Achieng"]


def test_elderly_update_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = client.post("/api/elderly", json=VALID_MEMBER, headers=auth_header(token)).get_json()["member"]
    resp = client.patch(f"/api/elderly/{member['id']}", json={"status": "Inactive"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["member"]["status"] == "Inactive"


def test_staff_cannot_delete_elderly_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    member = client.post("/api/elderly", json=VALID_MEMBER, headers=auth_header(token)).get_json()["member"]
    resp = client.delete(f"/api/elderly/{member['id']}", headers=auth_header(token))
    assert resp.status_code == 403


def test_admin_can_delete_elderly_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = client.post("/api/elderly", json=VALID_MEMBER, headers=auth_header(token)).get_json()["member"]
    resp = client.delete(f"/api/elderly/{member['id']}", headers=auth_header(token))
    assert resp.status_code == 204
