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
