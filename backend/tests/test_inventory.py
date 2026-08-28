VALID_ITEM = {"name": "Rice", "category": "Food", "unit": "kg", "minimum_stock": 10}


def test_staff_can_create_item(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["item"]
    assert body["name"] == "Rice"
    assert body["current_stock"] == 0.0
    assert body["low_stock"] is True  # 0 <= minimum_stock (10)


def test_current_stock_is_not_client_settable_on_create(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/inventory", json={**VALID_ITEM, "current_stock": 500}, headers=auth_header(token))
    # marshmallow rejects the unknown field outright (schema has no such field)
    assert resp.status_code == 400


def test_volunteer_cannot_create_item(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_create_rejects_duplicate_name(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token))
    resp = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token))
    assert resp.status_code == 409


def test_create_rejects_invalid_category(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/inventory", json={**VALID_ITEM, "category": "Vehicles"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_minimum_stock_persists_across_partial_edit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    patched = client.patch(f"/api/inventory/{item['id']}", json={"notes": "Stored in the back pantry"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["item"]["minimum_stock"] == 10.0
    assert patched.get_json()["item"]["notes"] == "Stored in the back pantry"


def test_update_rejects_current_stock_field(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    resp = client.patch(f"/api/inventory/{item['id']}", json={"current_stock": 999}, headers=auth_header(token))
    assert resp.status_code == 400  # unknown field — the only way to change stock is a movement


def test_list_filters_by_category_and_low_stock(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    rice = client.post("/api/inventory", json={"name": "Rice", "category": "Food", "unit": "kg", "minimum_stock": 10}, headers=auth_header(token)).get_json()["item"]
    gloves = client.post("/api/inventory", json={"name": "Gloves", "category": "Medical", "unit": "boxes", "minimum_stock": 2}, headers=auth_header(token)).get_json()["item"]
    # Rice stays at 0 (below its minimum of 10); Gloves gets stocked above its minimum of 2.
    client.post(f"/api/inventory/{gloves['id']}/movements", json={"movement_type": "In", "quantity": 20}, headers=auth_header(token))

    food_only = client.get("/api/inventory?category=Food", headers=auth_header(token))
    assert len(food_only.get_json()["items"]) == 1

    low_stock = client.get("/api/inventory?low_stock=true", headers=auth_header(token))
    names = [i["name"] for i in low_stock.get_json()["items"]]
    assert "Rice" in names  # 0 stock <= 10 minimum
    assert "Gloves" not in names  # 20 stock > 2 minimum


# ---------- Stock movements ----------

def test_stock_in_increases_current_stock(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]

    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 50, "reason": "Donation received"}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["item"]["current_stock"] == 50.0
    assert resp.get_json()["movement"]["movement_type"] == "In"


def test_stock_out_decreases_current_stock(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 50}, headers=auth_header(token))

    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Out", "quantity": 20, "reason": "Used for lunch service"}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["item"]["current_stock"] == 30.0


def test_stock_out_rejects_insufficient_stock(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Out", "quantity": 5}, headers=auth_header(token))
    assert resp.status_code == 400
    # current_stock must remain untouched by the rejected movement
    unchanged = client.get(f"/api/inventory/{item['id']}", headers=auth_header(token))
    assert unchanged.get_json()["item"]["current_stock"] == 0.0


def test_stock_out_exactly_to_zero_is_allowed(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 20}, headers=auth_header(token))

    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Out", "quantity": 20}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["item"]["current_stock"] == 0.0


def test_movement_rejects_zero_or_negative_quantity(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 0}, headers=auth_header(token))
    assert resp.status_code == 400


def test_movement_rejects_invalid_type(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Sideways", "quantity": 5}, headers=auth_header(token))
    assert resp.status_code == 400


def test_movement_rejects_unknown_item(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/inventory/999/movements", json={"movement_type": "In", "quantity": 5}, headers=auth_header(token))
    assert resp.status_code == 404


def test_volunteer_cannot_create_movement(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(admin_token)).get_json()["item"]
    _, access_token, _ = make_user()
    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 5}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_expiry_date_only_applied_to_in_movements(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 50}, headers=auth_header(token))

    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Out", "quantity": 10, "expiry_date": "2026-12-31"}, headers=auth_header(token))
    assert resp.get_json()["movement"]["expiry_date"] is None  # ignored for Out


def test_movement_links_to_a_donation(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    donation = client.post("/api/admin/donations", json={"donation_type": "Food", "donor_name": "Local Grocer", "item_description": "50kg rice", "quantity": 50, "unit": "kg"}, headers=auth_header(token)).get_json()["donation"]

    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 50, "donation_id": donation["id"]}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["movement"]["donation_id"] == donation["id"]


def test_movement_rejects_unknown_donation(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    resp = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 5, "donation_id": 999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_list_movements_for_an_item(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 50}, headers=auth_header(token))
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "Out", "quantity": 10}, headers=auth_header(token))

    resp = client.get(f"/api/inventory/{item['id']}/movements", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.get_json()["movements"]) == 2


def test_sequence_of_movements_keeps_balance_correct(client, make_staff_user, auth_header):
    """Regression: the running balance must always equal sum(In) - sum(Out)."""
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    steps = [("In", 100), ("Out", 30), ("In", 20), ("Out", 45), ("Out", 5)]
    for movement_type, qty in steps:
        r = client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": movement_type, "quantity": qty}, headers=auth_header(token))
        assert r.status_code == 201

    final = client.get(f"/api/inventory/{item['id']}", headers=auth_header(token))
    assert final.get_json()["item"]["current_stock"] == 40.0  # 100-30+20-45-5


# ---------- Delete ----------

def test_admin_can_delete_item_with_no_movements(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    resp = client.delete(f"/api/inventory/{item['id']}", headers=auth_header(token))
    assert resp.status_code == 204


def test_cannot_delete_item_with_movement_history(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 10}, headers=auth_header(token))

    resp = client.delete(f"/api/inventory/{item['id']}", headers=auth_header(token))
    assert resp.status_code == 409


def test_staff_cannot_delete_item(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    item = client.post("/api/inventory", json=VALID_ITEM, headers=auth_header(token)).get_json()["item"]
    resp = client.delete(f"/api/inventory/{item['id']}", headers=auth_header(token))
    assert resp.status_code == 403
