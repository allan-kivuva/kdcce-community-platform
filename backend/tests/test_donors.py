VALID_DONOR = {"name": "Amina K.", "email": "amina@example.com", "phone": "0700000000", "donor_type": "Individual"}


def test_admin_can_create_donor(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/donors", json=VALID_DONOR, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["donor"]["name"] == "Amina K."
    assert resp.get_json()["donor"]["email"] == "amina@example.com"


def test_staff_can_create_donor(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/donors", json=VALID_DONOR, headers=auth_header(token))
    assert resp.status_code == 201


def test_volunteer_cannot_create_donor(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/donors", json=VALID_DONOR, headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_donors(client):
    assert client.get("/api/donors").status_code == 401


def test_unauthenticated_cannot_access_donor_detail(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post("/api/donors", json=VALID_DONOR, headers=auth_header(token)).get_json()["donor"]
    assert client.get(f"/api/donors/{created['id']}").status_code == 401


def test_volunteer_cannot_access_donor_detail(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/donors", json=VALID_DONOR, headers=auth_header(admin_token)).get_json()["donor"]
    _, vol_token, _ = make_user()
    resp = client.get(f"/api/donors/{created['id']}", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_admin_can_update_donor(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post("/api/donors", json=VALID_DONOR, headers=auth_header(token)).get_json()["donor"]
    resp = client.patch(f"/api/donors/{created['id']}", json={"notes": "Prefers M-Pesa", "phone": "0711111111"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["donor"]["notes"] == "Prefers M-Pesa"
    assert resp.get_json()["donor"]["phone"] == "0711111111"


def test_volunteer_cannot_update_donor(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/donors", json=VALID_DONOR, headers=auth_header(admin_token)).get_json()["donor"]
    _, vol_token, _ = make_user()
    resp = client.patch(f"/api/donors/{created['id']}", json={"notes": "hacked"}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_donor_search_by_name_or_email(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/donors", json={"name": "Zebra Corp", "email": "zebra@example.com", "donor_type": "Organization"}, headers=auth_header(token))
    client.post("/api/donors", json={"name": "Someone Else", "email": "else@example.com"}, headers=auth_header(token))

    resp = client.get("/api/donors?q=zebra", headers=auth_header(token))
    names = [d["name"] for d in resp.get_json()["donors"]]
    assert names == ["Zebra Corp"]


# ---------- Donation linking / auto-resolution ----------

def test_public_donation_auto_links_to_new_donor(client):
    resp = client.post("/api/donations", json={
        "donor_name": "Fresh Donor", "donor_email": "fresh@example.com", "amount": 1000,
        "frequency": "one-time",
    })
    assert resp.status_code == 201
    donation = resp.get_json()["donation"]
    assert donation["donor_id"] is not None


def test_repeat_donation_links_to_same_donor(client):
    r1 = client.post("/api/donations", json={"donor_name": "Repeat Donor", "donor_email": "repeat@example.com", "amount": 500, "frequency": "one-time"})
    r2 = client.post("/api/donations", json={"donor_name": "Repeat Donor Again", "donor_email": "REPEAT@example.com", "amount": 700, "frequency": "one-time"})
    donor_id_1 = r1.get_json()["donation"]["donor_id"]
    donor_id_2 = r2.get_json()["donation"]["donor_id"]
    assert donor_id_1 is not None
    assert donor_id_1 == donor_id_2


def test_donation_without_email_is_not_linked_to_a_donor(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/donations", json={
        "donation_type": "Food", "donor_name": "Anonymous", "item_description": "Rice", "quantity": 10, "unit": "kg",
    }, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["donation"]["donor_id"] is None


def test_donor_detail_shows_lifetime_amount_and_donation_count(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/donations", json={"donor_name": "Repeat Giver", "donor_email": "giver@example.com", "amount": 1000, "frequency": "one-time"})
    client.post("/api/donations", json={"donor_name": "Repeat Giver", "donor_email": "giver@example.com", "amount": 500, "frequency": "one-time"})

    donors = client.get("/api/donors?q=giver", headers=auth_header(token)).get_json()["donors"]
    donor_id = donors[0]["id"]
    resp = client.get(f"/api/donors/{donor_id}", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["donor"]["lifetime_amount"] == 1500
    assert body["donor"]["donation_count"] == 2
    assert len(body["donations"]) == 2


def test_donor_lifetime_amount_excludes_pending_donations(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post("/api/donations", json={"donor_name": "Pending Giver", "donor_email": "pending@example.com", "amount": 900, "frequency": "one-time"}).get_json()["donation"]
    client.patch(f"/api/donations/{created['id']}", json={"status": "Pending"}, headers=auth_header(token))

    donors = client.get("/api/donors?q=pending", headers=auth_header(token)).get_json()["donors"]
    donor_id = donors[0]["id"]
    resp = client.get(f"/api/donors/{donor_id}", headers=auth_header(token))
    body = resp.get_json()
    assert body["donor"]["lifetime_amount"] == 0
    assert body["donor"]["donation_count"] == 1  # still counted in history, just not lifetime $
