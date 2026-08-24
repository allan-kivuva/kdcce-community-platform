def test_new_volunteer_has_a_pending_profile(client, make_user, auth_header):
    _, access_token, _ = make_user(email="vol1@example.com")
    resp = client.get("/api/volunteers/me", headers=auth_header(access_token))
    assert resp.status_code == 200
    body = resp.get_json()["volunteer"]
    assert body["status"] == "Pending"
    assert body["email"] == "vol1@example.com"


def test_staff_has_no_volunteer_profile(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.get("/api/volunteers/me", headers=auth_header(token))
    assert resp.status_code == 404


def test_volunteer_can_edit_own_profile(client, make_user, auth_header):
    _, access_token, _ = make_user(email="vol2@example.com")
    resp = client.patch("/api/volunteers/me", json={"skills": "Cooking, first aid", "availability": "Weekday mornings"}, headers=auth_header(access_token))
    assert resp.status_code == 200
    body = resp.get_json()["volunteer"]
    assert body["skills"] == "Cooking, first aid"
    assert body["status"] == "Pending"  # unchanged


def test_volunteer_cannot_set_own_status(client, make_user, auth_header):
    _, access_token, _ = make_user(email="vol3@example.com")
    resp = client.patch("/api/volunteers/me", json={"status": "Verified"}, headers=auth_header(access_token))
    assert resp.status_code == 400  # "status" is not a field on the self-update schema


def test_self_update_partial_edit_does_not_clear_other_fields(client, make_user, auth_header):
    _, access_token, _ = make_user(email="vol4@example.com")
    client.patch("/api/volunteers/me", json={"skills": "Cooking", "bio": "Loves the elderly"}, headers=auth_header(access_token))
    patched = client.patch("/api/volunteers/me", json={"availability": "Weekends"}, headers=auth_header(access_token))
    body = patched.get_json()["volunteer"]
    assert body["skills"] == "Cooking"
    assert body["bio"] == "Loves the elderly"
    assert body["availability"] == "Weekends"


def test_me_requires_auth(client):
    resp = client.get("/api/volunteers/me")
    assert resp.status_code == 401


# ---------- Application (extends the same self-update path) ----------

def test_volunteer_can_submit_full_application_via_self_update(client, make_user, auth_header):
    """The public 'Become a Volunteer' flow is register, then this PATCH —
    no separate application endpoint. All of these fields must round-trip."""
    _, access_token, _ = make_user(email="applicant1@example.com")
    resp = client.patch(
        "/api/volunteers/me",
        json={
            "phone": "0712345678",
            "skills": "First aid, community outreach",
            "availability": "Weekends",
            "areas_of_interest": "Home visits, feeding program",
            "experience": "Two years volunteering at a local shelter",
            "motivation": "I want to give back to my community",
            "bio": "Retired teacher, enjoys spending time with elders",
        },
        headers=auth_header(access_token),
    )
    assert resp.status_code == 200
    body = resp.get_json()["volunteer"]
    assert body["areas_of_interest"] == "Home visits, feeding program"
    assert body["experience"] == "Two years volunteering at a local shelter"
    assert body["motivation"] == "I want to give back to my community"
    assert body["status"] == "Pending"


def test_applicant_cannot_set_rejection_reason_on_self(client, make_user, auth_header):
    _, access_token, _ = make_user(email="applicant2@example.com")
    resp = client.patch("/api/volunteers/me", json={"rejection_reason": "I approve myself"}, headers=auth_header(access_token))
    assert resp.status_code == 400  # not a field on the self-update schema


def test_applicant_cannot_approve_self_via_crafted_payload(client, make_user, auth_header):
    """A payload mixing a legitimate self-editable field with status must
    be rejected wholesale — marshmallow's unknown-field handling means the
    whole request 400s rather than silently dropping just 'status'."""
    _, access_token, _ = make_user(email="applicant3@example.com")
    resp = client.patch(
        "/api/volunteers/me",
        json={"bio": "Trustworthy, promise", "status": "Verified"},
        headers=auth_header(access_token),
    )
    assert resp.status_code == 400
    profile = client.get("/api/volunteers/me", headers=auth_header(access_token)).get_json()["volunteer"]
    assert profile["status"] == "Pending"


# ---------- Staff management ----------

def test_staff_can_list_volunteers(client, make_user, make_staff_user, auth_header):
    make_user(email="vol5@example.com")
    _, token = make_staff_user("admin")
    resp = client.get("/api/volunteers", headers=auth_header(token))
    assert resp.status_code == 200
    assert any(v["email"] == "vol5@example.com" for v in resp.get_json()["volunteers"])


def test_volunteer_cannot_list_all_volunteers(client, make_user, auth_header):
    _, access_token, _ = make_user(email="vol6@example.com")
    resp = client.get("/api/volunteers", headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_volunteers(client):
    resp = client.get("/api/volunteers")
    assert resp.status_code == 401


def test_staff_can_verify_a_volunteer(client, make_user, make_staff_user, auth_header):
    _, _, _ = make_user(email="vol7@example.com")
    admin_user, admin_token = make_staff_user("admin")
    volunteer_id = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"][0]["id"]

    resp = client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "Verified"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    body = resp.get_json()["volunteer"]
    assert body["status"] == "Verified"
    assert body["reviewed_by"] == admin_user["name"]
    assert body["reviewed_at"] is not None


def test_status_persists_across_partial_edit_by_staff(client, make_user, make_staff_user, auth_header):
    """Regression: PATCHing without status must not reset it back to Pending."""
    make_user(email="vol8@example.com")
    _, token = make_staff_user("admin")
    volunteer_id = client.get("/api/volunteers", headers=auth_header(token)).get_json()["volunteers"][0]["id"]
    client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "Verified"}, headers=auth_header(token))

    patched = client.patch(f"/api/volunteers/{volunteer_id}", json={"phone": "0712345678"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["volunteer"]["status"] == "Verified"
    assert patched.get_json()["volunteer"]["phone"] == "0712345678"


def test_volunteer_rejects_invalid_status(client, make_user, make_staff_user, auth_header):
    make_user(email="vol9@example.com")
    _, token = make_staff_user("admin")
    volunteer_id = client.get("/api/volunteers", headers=auth_header(token)).get_json()["volunteers"][0]["id"]
    resp = client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "SuperVolunteer"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_staff_can_reject_with_a_reason(client, make_user, make_staff_user, auth_header):
    make_user(email="vol11@example.com")
    _, token = make_staff_user("admin")
    volunteer_id = client.get("/api/volunteers", headers=auth_header(token)).get_json()["volunteers"][0]["id"]

    resp = client.patch(
        f"/api/volunteers/{volunteer_id}",
        json={"status": "Rejected", "rejection_reason": "We currently have enough volunteers for this area."},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    body = resp.get_json()["volunteer"]
    assert body["status"] == "Rejected"
    assert body["rejection_reason"] == "We currently have enough volunteers for this area."


def test_rejection_reason_is_cleared_on_a_later_reversal(client, make_user, make_staff_user, auth_header):
    make_user(email="vol12@example.com")
    _, token = make_staff_user("admin")
    volunteer_id = client.get("/api/volunteers", headers=auth_header(token)).get_json()["volunteers"][0]["id"]
    client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "Rejected", "rejection_reason": "Not a fit right now."}, headers=auth_header(token))

    reversed_ = client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "Verified"}, headers=auth_header(token))
    assert reversed_.get_json()["volunteer"]["rejection_reason"] is None


def test_list_filters_by_status(client, make_user, make_staff_user, auth_header):
    make_user(email="vol10@example.com")
    _, token = make_staff_user("admin")
    volunteer_id = client.get("/api/volunteers", headers=auth_header(token)).get_json()["volunteers"][0]["id"]
    client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "Verified"}, headers=auth_header(token))

    verified = client.get("/api/volunteers?status=Verified", headers=auth_header(token))
    assert len(verified.get_json()["volunteers"]) == 1
    pending = client.get("/api/volunteers?status=Pending", headers=auth_header(token))
    assert len(pending.get_json()["volunteers"]) == 0
