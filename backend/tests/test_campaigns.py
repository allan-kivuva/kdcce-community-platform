VALID_CAMPAIGN = {"name": "Feeding Drive 2026", "goal_amount": 500000, "status": "Active", "public_visible": True}


def test_admin_can_create_campaign(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/campaigns", json=VALID_CAMPAIGN, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["campaign"]
    assert body["name"] == "Feeding Drive 2026"
    assert body["goal_amount"] == 500000.0
    assert body["progress"]["raised_amount"] == 0


def test_staff_can_create_campaign(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/admin/campaigns", json=VALID_CAMPAIGN, headers=auth_header(token))
    assert resp.status_code == 201


def test_volunteer_cannot_create_campaign(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/admin/campaigns", json=VALID_CAMPAIGN, headers=auth_header(token))
    assert resp.status_code == 403


def test_create_rejects_zero_goal(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "goal_amount": 0}, headers=auth_header(token))
    assert resp.status_code == 400


def test_campaign_can_link_to_a_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json={"name": "Feeding Program", "status": "Active"}, headers=auth_header(token)).get_json()["program"]
    resp = client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "program_id": program["id"]}, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["campaign"]["program_name"] == "Feeding Program"


def test_campaign_rejects_unknown_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "program_id": 999999}, headers=auth_header(token))
    assert resp.status_code == 400


def test_admin_can_edit_and_change_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post("/api/admin/campaigns", json=VALID_CAMPAIGN, headers=auth_header(token)).get_json()["campaign"]
    resp = client.patch(f"/api/admin/campaigns/{created['id']}", json={"status": "Paused"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["campaign"]["status"] == "Paused"


def test_volunteer_cannot_view_admin_campaign_list(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.get("/api/admin/campaigns", headers=auth_header(token))
    assert resp.status_code == 403


def test_slug_must_be_unique(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "slug": "feeding-2026"}, headers=auth_header(token))
    resp = client.post("/api/admin/campaigns", json={"name": "Another", "goal_amount": 1000, "slug": "feeding-2026"}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Progress / goal calculation ----------

def test_progress_counts_only_paid_and_received_donations(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    campaign = client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "goal_amount": 1000}, headers=auth_header(token)).get_json()["campaign"]

    d1 = client.post("/api/donations", json={"donor_name": "A", "donor_email": "a@example.com", "amount": 400, "frequency": "one-time"}).get_json()["donation"]
    d2 = client.post("/api/donations", json={"donor_name": "B", "donor_email": "b@example.com", "amount": 300, "frequency": "one-time"}).get_json()["donation"]
    client.patch(f"/api/donations/{d1['id']}", json={"campaign_id": campaign["id"]}, headers=auth_header(token))
    client.patch(f"/api/donations/{d2['id']}", json={"campaign_id": campaign["id"], "status": "Pending"}, headers=auth_header(token))

    resp = client.get(f"/api/admin/campaigns/{campaign['id']}", headers=auth_header(token))
    progress = resp.get_json()["campaign"]["progress"]
    assert progress["raised_amount"] == 400  # the Pending one excluded
    assert progress["donation_count"] == 1
    assert progress["remaining_amount"] == 600
    assert progress["percent_achieved"] == 40.0


def test_progress_with_no_donations_is_zero(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    campaign = client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "goal_amount": 1000}, headers=auth_header(token)).get_json()["campaign"]
    resp = client.get(f"/api/admin/campaigns/{campaign['id']}", headers=auth_header(token))
    progress = resp.get_json()["campaign"]["progress"]
    assert progress["raised_amount"] == 0
    assert progress["percent_achieved"] == 0.0


# ---------- Donation linking ----------

def test_new_donation_auto_links_to_matching_campaign_by_exact_name(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    campaign = client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "name": "Water Wells"}, headers=auth_header(token)).get_json()["campaign"]

    resp = client.post("/api/donations", json={"donor_name": "C", "donor_email": "c@example.com", "amount": 100, "frequency": "one-time", "campaign": "Water Wells"})
    assert resp.get_json()["donation"]["campaign_id"] == campaign["id"]


def test_donation_campaign_text_not_matching_any_campaign_stays_unlinked(client):
    resp = client.post("/api/donations", json={"donor_name": "D", "donor_email": "d@example.com", "amount": 100, "frequency": "one-time", "campaign": "Some Unrelated Thing"})
    assert resp.get_json()["donation"]["campaign_id"] is None


def test_link_donations_action_links_pre_existing_free_text_matches(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    # Donation created BEFORE the campaign exists — free text only.
    client.post("/api/donations", json={"donor_name": "E", "donor_email": "e@example.com", "amount": 250, "frequency": "one-time", "campaign": "School Fees"})

    campaign = client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "name": "School Fees"}, headers=auth_header(token)).get_json()["campaign"]
    resp = client.post(f"/api/admin/campaigns/{campaign['id']}/link-donations", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["linked_count"] == 1

    progress = client.get(f"/api/admin/campaigns/{campaign['id']}", headers=auth_header(token)).get_json()["campaign"]["progress"]
    assert progress["raised_amount"] == 250


def test_link_donations_is_case_insensitive_exact_match_only(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/donations", json={"donor_name": "F", "donor_email": "f@example.com", "amount": 100, "frequency": "one-time", "campaign": "Partial Match Only"})
    campaign = client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "name": "Partial Match"}, headers=auth_header(token)).get_json()["campaign"]
    resp = client.post(f"/api/admin/campaigns/{campaign['id']}/link-donations", headers=auth_header(token))
    assert resp.get_json()["linked_count"] == 0  # "Partial Match Only" != "Partial Match"


# ---------- Public visibility ----------

def test_public_sees_only_public_visible_active_campaigns(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "name": "Public Active", "public_visible": True, "status": "Active"}, headers=auth_header(token))
    client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "name": "Private Active", "public_visible": False, "status": "Active"}, headers=auth_header(token))
    client.post("/api/admin/campaigns", json={**VALID_CAMPAIGN, "name": "Public Draft", "public_visible": True, "status": "Draft"}, headers=auth_header(token))

    resp = client.get("/api/campaigns")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.get_json()["campaigns"]]
    assert names == ["Public Active"]


def test_public_campaign_response_excludes_internal_fields(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/campaigns", json=VALID_CAMPAIGN, headers=auth_header(token))
    resp = client.get("/api/campaigns")
    campaign = resp.get_json()["campaigns"][0]
    assert "created_by" not in campaign
    assert "created_at" not in campaign
    assert "public_visible" not in campaign
