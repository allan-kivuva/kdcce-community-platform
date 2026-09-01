from app.models import AuditLog

VALID_ITEM = {"name": "Rice", "category": "Food", "unit": "kg", "minimum_stock": 10}


def _stocked_item(client, token, auth_header, quantity=50, **overrides):
    item = client.post("/api/inventory", json={**VALID_ITEM, **overrides}, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": quantity}, headers=auth_header(token))
    return client.get(f"/api/inventory/{item['id']}", headers=auth_header(token)).get_json()["item"]


def _member(client, token, auth_header, name="Mary Achieng"):
    return client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token)).get_json()["member"]


# ---------- Create ----------

def test_create_distribution_reduces_stock_and_creates_row(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = _stocked_item(client, token, auth_header, quantity=50)
    member = _member(client, token, auth_header)

    resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": member["id"], "quantity": 5, "reason": "Monthly food ration"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["distribution"]["quantity"] == 5.0
    assert body["distribution"]["elderly_member_id"] == member["id"]
    assert body["distribution"]["elderly_member_name"] == "Mary Achieng"
    assert body["item"]["current_stock"] == 45.0

    refreshed = client.get(f"/api/inventory/{item['id']}", headers=auth_header(token)).get_json()["item"]
    assert refreshed["current_stock"] == 45.0


def test_create_distribution_with_insufficient_stock_is_rejected_and_unchanged(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = _stocked_item(client, token, auth_header, quantity=3)
    member = _member(client, token, auth_header)

    resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": member["id"], "quantity": 10},
        headers=auth_header(token),
    )
    assert resp.status_code == 400

    refreshed = client.get(f"/api/inventory/{item['id']}", headers=auth_header(token)).get_json()["item"]
    assert refreshed["current_stock"] == 3.0

    listed = client.get("/api/inventory/distributions", headers=auth_header(token)).get_json()["distributions"]
    assert listed == []


def test_create_distribution_rejects_unknown_elderly_member(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = _stocked_item(client, token, auth_header, quantity=50)

    resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": 999, "quantity": 5},
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_create_distribution_rejects_unknown_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = _stocked_item(client, token, auth_header, quantity=50)
    member = _member(client, token, auth_header)

    resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": member["id"], "quantity": 5, "program_id": 999},
        headers=auth_header(token),
    )
    assert resp.status_code == 400


# ---------- Program link ----------

def test_distribution_linked_to_program_returns_program_name(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = _stocked_item(client, token, auth_header, quantity=50)
    member = _member(client, token, auth_header)
    program = client.post("/api/programs", json={"name": "Feeding Program"}, headers=auth_header(token)).get_json()["program"]

    resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": member["id"], "quantity": 5, "program_id": program["id"]},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.get_json()["distribution"]["program_id"] == program["id"]
    assert resp.get_json()["distribution"]["program_name"] == "Feeding Program"


def test_distribution_without_program_has_null_program_name(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = _stocked_item(client, token, auth_header, quantity=50)
    member = _member(client, token, auth_header)

    resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": member["id"], "quantity": 5},
        headers=auth_header(token),
    )
    assert resp.get_json()["distribution"]["program_id"] is None
    assert resp.get_json()["distribution"]["program_name"] is None


# ---------- Listing / filtering ----------

def test_list_distributions_filters_by_elderly_member_and_item(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item_a = _stocked_item(client, token, auth_header, quantity=50, name="Rice")
    item_b = _stocked_item(client, token, auth_header, quantity=50, name="Beans")
    member_a = _member(client, token, auth_header, name="Mary Achieng")
    member_b = _member(client, token, auth_header, name="John Otieno")

    client.post(f"/api/inventory/{item_a['id']}/distributions", json={"elderly_member_id": member_a["id"], "quantity": 5}, headers=auth_header(token))
    client.post(f"/api/inventory/{item_a['id']}/distributions", json={"elderly_member_id": member_b["id"], "quantity": 3}, headers=auth_header(token))
    client.post(f"/api/inventory/{item_b['id']}/distributions", json={"elderly_member_id": member_a["id"], "quantity": 2}, headers=auth_header(token))

    all_dist = client.get("/api/inventory/distributions", headers=auth_header(token)).get_json()["distributions"]
    assert len(all_dist) == 3

    by_member = client.get(f"/api/inventory/distributions?elderly_member_id={member_a['id']}", headers=auth_header(token)).get_json()["distributions"]
    assert len(by_member) == 2
    assert all(d["elderly_member_id"] == member_a["id"] for d in by_member)

    by_item = client.get(f"/api/inventory/distributions?item_id={item_b['id']}", headers=auth_header(token)).get_json()["distributions"]
    assert len(by_item) == 1
    assert by_item[0]["item_id"] == item_b["id"]


# ---------- Low-stock notification parity ----------

def test_distribution_triggers_low_stock_notification_same_as_plain_movement(client, make_staff_user, auth_header):
    admin_user, admin_token = make_staff_user("admin")
    staff_user, staff_token = make_staff_user("staff", email="dist-staff@example.com")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(admin_token)).get_json()["item"]  # minimum_stock=10
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 20}, headers=auth_header(admin_token))
    member = _member(client, admin_token, auth_header)

    assert client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"] == []

    # 20 -> 5 crosses at/below the minimum of 10.
    resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": member["id"], "quantity": 15},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 201

    admin_notifs = client.get("/api/notifications", headers=auth_header(admin_token)).get_json()["notifications"]
    staff_notifs = client.get("/api/notifications", headers=auth_header(staff_token)).get_json()["notifications"]
    assert len(admin_notifs) == 1
    assert len(staff_notifs) == 1
    assert admin_notifs[0]["notification_type"] == "Low Inventory Alert"


# ---------- Access control ----------

def test_volunteer_cannot_create_or_list_distributions(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    item = _stocked_item(client, admin_token, auth_header, quantity=50)
    member = _member(client, admin_token, auth_header)
    _, access_token, _ = make_user()

    create_resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": member["id"], "quantity": 5},
        headers=auth_header(access_token),
    )
    assert create_resp.status_code == 403

    list_resp = client.get("/api/inventory/distributions", headers=auth_header(access_token))
    assert list_resp.status_code == 403


def test_unauthenticated_cannot_create_or_list_distributions(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    item = _stocked_item(client, admin_token, auth_header, quantity=50)
    member = _member(client, admin_token, auth_header)

    create_resp = client.post(f"/api/inventory/{item['id']}/distributions", json={"elderly_member_id": member["id"], "quantity": 5})
    assert create_resp.status_code == 401

    list_resp = client.get("/api/inventory/distributions")
    assert list_resp.status_code == 401


# ---------- Audit logging ----------

def test_create_distribution_creates_audit_log_row(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = _stocked_item(client, token, auth_header, quantity=50)
    member = _member(client, token, auth_header)

    resp = client.post(
        f"/api/inventory/{item['id']}/distributions",
        json={"elderly_member_id": member["id"], "quantity": 5},
        headers=auth_header(token),
    )
    distribution_id = resp.get_json()["distribution"]["id"]

    logs = AuditLog.query.filter_by(resource_type="distribution", action="create").all()
    assert len(logs) == 1
    assert logs[0].resource_id == distribution_id
