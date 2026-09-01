def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com", name="Vera Volunteer"):
    user, access_token, _ = make_user(email=email, name=name)
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _create_activity(client, token, auth_header, **overrides):
    payload = {"title": "Community Fair", "activity_type": "Community Event", "scheduled_at": "2027-03-15T09:00:00+00:00", **overrides}
    return client.post("/api/activities", json=payload, headers=auth_header(token)).get_json()["activity"]


# ---------- Capacity ----------

def test_unlimited_capacity_accepts_any_number_of_rsvps(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    for i in range(3):
        _, tok = _verified_volunteer(client, make_user, auth_header, admin_token, email=f"unlimited{i}@example.com")
        resp = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
        assert resp.status_code == 201
        assert resp.get_json()["assignment"]["status"] == "Confirmed"


def test_exact_capacity_confirms_up_to_the_limit(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, capacity=2)
    statuses = []
    for i in range(2):
        _, tok = _verified_volunteer(client, make_user, auth_header, admin_token, email=f"exact{i}@example.com")
        resp = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
        statuses.append(resp.get_json()["assignment"]["status"])
    assert statuses == ["Confirmed", "Confirmed"]


def test_over_capacity_rsvp_goes_to_waitlist(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, capacity=1)
    _, tok1 = _verified_volunteer(client, make_user, auth_header, admin_token, email="first@example.com")
    _, tok2 = _verified_volunteer(client, make_user, auth_header, admin_token, email="second@example.com")

    r1 = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))
    r2 = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok2))
    assert r1.get_json()["assignment"]["status"] == "Confirmed"
    assert r2.get_json()["assignment"]["status"] == "Waitlisted"

    activity_view = client.get(f"/api/activities/{activity['id']}", headers=auth_header(admin_token)).get_json()["activity"]
    assert activity_view["confirmed_volunteer_count"] == 1
    assert activity_view["spots_remaining"] == 0
    assert activity_view["waitlist_count"] == 1


def test_closed_registration_rejects_rsvp(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, registration_open=False)
    _, tok = _verified_volunteer(client, make_user, auth_header, admin_token)
    resp = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
    assert resp.status_code == 409


def test_past_registration_deadline_rejects_rsvp(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, registration_deadline="2020-01-01T00:00:00+00:00")
    _, tok = _verified_volunteer(client, make_user, auth_header, admin_token)
    resp = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
    assert resp.status_code == 409


# ---------- RSVP ----------

def test_volunteer_can_rsvp_and_see_own_status(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    _, tok = _verified_volunteer(client, make_user, auth_header, admin_token)

    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
    resp = client.get("/api/activities/me/assignments", headers=auth_header(tok))
    assignments = resp.get_json()["assignments"]
    assert len(assignments) == 1
    assert assignments[0]["is_self_rsvp"] is True
    assert assignments[0]["role"] == "General Volunteer"
    assert assignments[0]["activity"]["id"] == activity["id"]


def test_duplicate_rsvp_rejected(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    _, tok = _verified_volunteer(client, make_user, auth_header, admin_token)
    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
    resp = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
    assert resp.status_code == 409


def test_admin_cannot_rsvp_via_volunteer_endpoint(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    resp = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(admin_token))
    assert resp.status_code == 403


def test_volunteer_can_cancel_own_rsvp(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    _, tok = _verified_volunteer(client, make_user, auth_header, admin_token)
    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))

    resp = client.delete(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
    assert resp.status_code == 200
    assert resp.get_json()["assignment"]["status"] == "Cancelled"

    # Can RSVP again after cancelling
    resp = client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
    assert resp.status_code == 201
    assert resp.get_json()["assignment"]["status"] == "Confirmed"


def test_cancelling_with_no_active_rsvp_fails(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    _, tok, _ = make_user(email="neverrsvped@example.com")
    resp = client.delete(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok))
    assert resp.status_code == 409


def test_unauthenticated_cannot_rsvp(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header)
    resp = client.post(f"/api/activities/{activity['id']}/rsvp")
    assert resp.status_code == 401


# ---------- Waitlist promotion ----------

def test_cancellation_promotes_earliest_waitlisted_volunteer(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, capacity=1)
    _, tok1 = _verified_volunteer(client, make_user, auth_header, admin_token, email="promo1@example.com")
    _, tok2 = _verified_volunteer(client, make_user, auth_header, admin_token, email="promo2@example.com")
    _, tok3 = _verified_volunteer(client, make_user, auth_header, admin_token, email="promo3@example.com")

    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))  # Confirmed
    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok2))  # Waitlisted (1st in line)
    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok3))  # Waitlisted (2nd in line)

    client.delete(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))

    vol2_status = client.get("/api/activities/me/assignments", headers=auth_header(tok2)).get_json()["assignments"][0]["status"]
    vol3_status = client.get("/api/activities/me/assignments", headers=auth_header(tok3)).get_json()["assignments"][0]["status"]
    assert vol2_status == "Confirmed"  # earliest waitlisted promoted
    assert vol3_status == "Waitlisted"  # still waiting


def test_promotion_notifies_the_promoted_volunteer(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, capacity=1)
    _, tok1 = _verified_volunteer(client, make_user, auth_header, admin_token, email="notifyfirst@example.com")
    _, tok2 = _verified_volunteer(client, make_user, auth_header, admin_token, email="notifysecond@example.com")

    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))
    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok2))
    client.delete(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))

    notifications = client.get("/api/notifications", headers=auth_header(tok2)).get_json()["notifications"]
    assert any(n["notification_type"] == "Event Waitlist Promoted" for n in notifications)


def test_cancelling_a_waitlisted_rsvp_does_not_trigger_promotion(client, make_user, make_staff_user, auth_header):
    """Cancelling a row that was never occupying a confirmed slot must
    not free anything up (nothing to double-promote either)."""
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, capacity=1)
    _, tok1 = _verified_volunteer(client, make_user, auth_header, admin_token, email="occupiesslot@example.com")
    _, tok2 = _verified_volunteer(client, make_user, auth_header, admin_token, email="waitlistedonly@example.com")

    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))
    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok2))  # Waitlisted
    client.delete(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok2))  # cancel the waitlisted one

    vol1_status = client.get("/api/activities/me/assignments", headers=auth_header(tok1)).get_json()["assignments"][0]["status"]
    assert vol1_status == "Confirmed"  # untouched, was never displaced


def test_no_double_promotion_from_a_single_cancellation(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    activity = _create_activity(client, admin_token, auth_header, capacity=1)
    _, tok1 = _verified_volunteer(client, make_user, auth_header, admin_token, email="onlyone1@example.com")
    _, tok2 = _verified_volunteer(client, make_user, auth_header, admin_token, email="onlyone2@example.com")
    _, tok3 = _verified_volunteer(client, make_user, auth_header, admin_token, email="onlyone3@example.com")

    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))
    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok2))
    client.post(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok3))
    client.delete(f"/api/activities/{activity['id']}/rsvp", headers=auth_header(tok1))

    admin_view = client.get(f"/api/activities/{activity['id']}/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    confirmed = [v for v in admin_view if v["status"] == "Confirmed"]
    assert len(confirmed) == 1  # exactly one promoted, not both waitlisted rows
