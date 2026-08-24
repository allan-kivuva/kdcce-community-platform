import pytest

VALID_DONATION = {
    "donor_name": "Amina K.",
    "donor_email": "amina@example.com",
    "amount": 2500,
    "frequency": "one-time",
    "campaign": "Feeding program",
    "payment_method": "M-Pesa",
}


def test_public_can_create_donation(client):
    resp = client.post("/api/donations", json=VALID_DONATION)
    assert resp.status_code == 201
    donation = resp.get_json()["donation"]
    assert donation["donor_name"] == "Amina K."
    assert donation["status"] == "Paid"
    assert donation["receipt_id"].startswith("KDCCE-")
    assert donation["txn_id"].startswith("TXN-")


def test_donation_status_from_client_is_ignored(client):
    # A donor-facing client claiming its own payment already succeeded (or
    # anything else) must not be trusted — server always sets status.
    resp = client.post("/api/donations", json={**VALID_DONATION, "status": "some-other-value"})
    assert resp.status_code in (201, 400)  # 400 if marshmallow rejects the unknown field outright
    if resp.status_code == 201:
        assert resp.get_json()["donation"]["status"] == "Paid"


@pytest.mark.parametrize("amount", [0, -50])
def test_rejects_non_positive_amount(client, amount):
    resp = client.post("/api/donations", json={**VALID_DONATION, "amount": amount})
    assert resp.status_code == 400
    assert "amount" in resp.get_json()["details"]


def test_rejects_missing_required_field(client):
    payload = {k: v for k, v in VALID_DONATION.items() if k != "donor_email"}
    resp = client.post("/api/donations", json=payload)
    assert resp.status_code == 400
    assert "donor_email" in resp.get_json()["details"]


def test_rejects_invalid_frequency(client):
    resp = client.post("/api/donations", json={**VALID_DONATION, "frequency": "yearly"})
    assert resp.status_code == 400


def test_rejects_invalid_email(client):
    resp = client.post("/api/donations", json={**VALID_DONATION, "donor_email": "not-an-email"})
    assert resp.status_code == 400


def test_two_donations_get_distinct_receipt_and_txn_ids(client):
    first = client.post("/api/donations", json=VALID_DONATION).get_json()["donation"]
    second = client.post("/api/donations", json=VALID_DONATION).get_json()["donation"]
    assert first["receipt_id"] != second["receipt_id"]
    assert first["txn_id"] != second["txn_id"]


def test_admin_can_list_donations(client, make_staff_user, auth_header):
    client.post("/api/donations", json=VALID_DONATION)
    _, token = make_staff_user("admin")
    resp = client.get("/api/donations", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.get_json()["donations"]) == 1


def test_staff_can_list_donations(client, make_staff_user, auth_header):
    client.post("/api/donations", json=VALID_DONATION)
    _, token = make_staff_user("staff")
    resp = client.get("/api/donations", headers=auth_header(token))
    assert resp.status_code == 200


def test_volunteer_cannot_list_donations(client, make_user, auth_header):
    client.post("/api/donations", json=VALID_DONATION)
    _, access_token, _ = make_user()
    resp = client.get("/api/donations", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_donations(client):
    resp = client.get("/api/donations")
    assert resp.status_code == 401


def test_admin_can_update_donation_status(client, make_staff_user, auth_header):
    donation = client.post("/api/donations", json=VALID_DONATION).get_json()["donation"]
    _, token = make_staff_user("admin")
    resp = client.patch(
        f"/api/donations/{donation['id']}", json={"status": "Pending"}, headers=auth_header(token)
    )
    assert resp.status_code == 200
    assert resp.get_json()["donation"]["status"] == "Pending"


def test_volunteer_cannot_update_donation(client, make_user, auth_header):
    donation = client.post("/api/donations", json=VALID_DONATION).get_json()["donation"]
    _, access_token, _ = make_user()
    resp = client.patch(
        f"/api/donations/{donation['id']}", json={"status": "Pending"}, headers=auth_header(access_token)
    )
    assert resp.status_code == 403


def test_csv_export_requires_admin_or_staff(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.get("/api/donations/export.csv", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_csv_export_rejects_unauthenticated(client):
    resp = client.get("/api/donations/export.csv")
    assert resp.status_code == 401


def test_csv_export_returns_csv_for_admin(client, make_staff_user, auth_header):
    client.post("/api/donations", json=VALID_DONATION)
    _, token = make_staff_user("admin")
    resp = client.get("/api/donations/export.csv", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    body = resp.get_data(as_text=True)
    assert "Amina K." in body
    assert "Donor,Email,Amount" in body


def test_public_donation_defaults_to_cash_type(client):
    donation = client.post("/api/donations", json=VALID_DONATION).get_json()["donation"]
    assert donation["donation_type"] == "Cash"


def test_public_endpoint_ignores_client_supplied_donation_type(client):
    # DonationCreateSchema has no donation_type field — the public flow
    # can never create a Food/Equipment row.
    resp = client.post("/api/donations", json={**VALID_DONATION, "donation_type": "Food"})
    assert resp.status_code in (201, 400)
    if resp.status_code == 201:
        assert resp.get_json()["donation"]["donation_type"] == "Cash"


# ---------- Admin-logged donations (any type) ----------

VALID_FOOD = {"donation_type": "Food", "donor_name": "Local Grocer", "item_description": "50kg rice, 20L cooking oil", "quantity": 50, "unit": "kg"}
VALID_CASH_ADMIN = {"donation_type": "Cash", "donor_name": "Walk-in Donor", "amount": 3000}


def test_staff_can_log_a_food_donation(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/admin/donations", json=VALID_FOOD, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["donation"]
    assert body["donation_type"] == "Food"
    assert body["status"] == "Received"
    assert body["item_description"] == "50kg rice, 20L cooking oil"
    assert body["quantity"] == 50.0
    assert body["amount"] is None


def test_staff_can_log_equipment_donation(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/donations", json={"donation_type": "Equipment", "donor_name": "Hospital Trust", "item_description": "2 wheelchairs", "quantity": 2, "unit": "units"}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["donation"]["status"] == "Received"


def test_staff_can_log_a_walk_in_cash_donation(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/donations", json=VALID_CASH_ADMIN, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["donation"]
    assert body["status"] == "Paid"
    assert body["amount"] == 3000.0
    assert body["donor_email"] is None  # never required for the admin path


def test_food_donation_rejects_missing_item_description(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    payload = {k: v for k, v in VALID_FOOD.items() if k != "item_description"}
    resp = client.post("/api/admin/donations", json=payload, headers=auth_header(token))
    assert resp.status_code == 400
    assert "item_description" in resp.get_json()["details"]


def test_food_donation_rejects_missing_quantity_and_unit(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    payload = {"donation_type": "Food", "donor_name": "X", "item_description": "Beans"}
    resp = client.post("/api/admin/donations", json=payload, headers=auth_header(token))
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert "quantity" in details and "unit" in details


def test_cash_admin_donation_rejects_missing_amount(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/donations", json={"donation_type": "Cash", "donor_name": "X"}, headers=auth_header(token))
    assert resp.status_code == 400
    assert "amount" in resp.get_json()["details"]


def test_volunteer_cannot_log_admin_donation(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/admin/donations", json=VALID_FOOD, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_log_admin_donation(client):
    resp = client.post("/api/admin/donations", json=VALID_FOOD)
    assert resp.status_code == 401


def test_admin_donation_rejects_invalid_type(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/donations", json={**VALID_FOOD, "donation_type": "Crypto"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_donation_type_receipt_and_txn_ids_are_generated_for_in_kind_too(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    donation = client.post("/api/admin/donations", json=VALID_FOOD, headers=auth_header(token)).get_json()["donation"]
    assert donation["receipt_id"].startswith("KDCCE-")
    assert donation["txn_id"].startswith("TXN-")


# ---------- Listing/filtering by type ----------

def test_list_filters_by_donation_type(client, make_staff_user, auth_header):
    client.post("/api/donations", json=VALID_DONATION)  # Cash
    _, token = make_staff_user("admin")
    client.post("/api/admin/donations", json=VALID_FOOD, headers=auth_header(token))

    food_only = client.get("/api/donations?donation_type=Food", headers=auth_header(token))
    assert len(food_only.get_json()["donations"]) == 1
    assert food_only.get_json()["donations"][0]["donation_type"] == "Food"

    all_donations = client.get("/api/donations", headers=auth_header(token))
    assert len(all_donations.get_json()["donations"]) == 2


# ---------- Partial-PATCH regression (extended fields) ----------

def test_status_persists_across_partial_edit_of_in_kind_donation(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    donation = client.post("/api/admin/donations", json=VALID_FOOD, headers=auth_header(token)).get_json()["donation"]

    patched = client.patch(f"/api/donations/{donation['id']}", json={"item_description": "60kg rice"}, headers=auth_header(token))
    assert patched.status_code == 200
    body = patched.get_json()["donation"]
    assert body["status"] == "Received"  # unchanged, not reset
    assert body["item_description"] == "60kg rice"
    assert body["quantity"] == 50.0  # unchanged


def test_csv_export_includes_in_kind_donations(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/donations", json=VALID_FOOD, headers=auth_header(token))
    resp = client.get("/api/donations/export.csv", headers=auth_header(token))
    body = resp.get_data(as_text=True)
    header_row = body.splitlines()[0]
    assert header_row.endswith("Type,Item Description,Quantity,Unit")
    assert "Local Grocer" in body
    assert "50kg rice, 20L cooking oil" in body
