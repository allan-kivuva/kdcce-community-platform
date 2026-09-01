from app.models import Consent


def _create_member(admin_token, auth_header, client, full_name="Consent Test Member"):
    resp = client.post("/api/elderly", json={"full_name": full_name, "gender": "Male"}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    return resp.get_json()["member"]


def test_admin_can_grant_consent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    resp = client.post(
        "/api/consents",
        json={"elderly_member_id": member["id"], "consent_type": "Photo Use", "status": "Granted", "notes": "Verbal confirmation from family"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    body = resp.get_json()["consent"]
    assert body["status"] == "Granted"
    assert body["granted_at"] is not None
    assert body["withdrawn_at"] is None


def test_deny_consent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    resp = client.post(
        "/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Photo Use", "status": "Denied"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.get_json()["consent"]["status"] == "Denied"


def test_withdraw_consent_creates_a_new_row_not_an_edit(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Communication", "status": "Granted"}, headers=auth_header(token))
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Communication", "status": "Withdrawn"}, headers=auth_header(token))

    with app.app_context():
        rows = Consent.query.filter_by(elderly_member_id=member["id"], consent_type="Communication").all()
        assert len(rows) == 2  # append-only — both the grant and the withdrawal survive as separate rows
        assert {r.status for r in rows} == {"Granted", "Withdrawn"}


def test_current_status_reflects_the_latest_decision(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Data Sharing", "status": "Granted"}, headers=auth_header(token))
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Data Sharing", "status": "Withdrawn"}, headers=auth_header(token))

    resp = client.get(f"/api/consents?elderly_member_id={member['id']}&consent_type=Data Sharing", headers=auth_header(token))
    consents = resp.get_json()["consents"]
    assert len(consents) == 1  # default view: current status only
    assert consents[0]["status"] == "Withdrawn"


def test_history_view_shows_every_decision(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Data Sharing", "status": "Granted"}, headers=auth_header(token))
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Data Sharing", "status": "Withdrawn"}, headers=auth_header(token))
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Data Sharing", "status": "Granted"}, headers=auth_header(token))

    resp = client.get(f"/api/consents?elderly_member_id={member['id']}&history=true", headers=auth_header(token))
    consents = resp.get_json()["consents"]
    assert len(consents) == 3


def test_consent_never_deleted(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Emergency Contact Access", "status": "Granted"}, headers=auth_header(token))
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Emergency Contact Access", "status": "Withdrawn"}, headers=auth_header(token))

    # There is deliberately no DELETE endpoint on /api/consents at all.
    with app.app_context():
        assert Consent.query.filter_by(elderly_member_id=member["id"]).count() == 2


def test_consent_changes_are_audited(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    client.post("/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Photo Use", "status": "Granted"}, headers=auth_header(token))

    resp = client.get("/api/audit-logs?resource_type=consent", headers=auth_header(token))
    rows = resp.get_json()["audit_logs"]
    assert any(r["action"] == "record" for r in rows)


def test_invalid_consent_type_rejected(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    resp = client.post(
        "/api/consents", json={"elderly_member_id": member["id"], "consent_type": "Not A Real Type", "status": "Granted"},
        headers=auth_header(token),
    )
    assert resp.status_code == 400


def test_volunteer_and_unauthenticated_cannot_touch_consents(client, make_user, auth_header):
    _, token, _ = make_user()
    assert client.get("/api/consents").status_code == 401
    assert client.get("/api/consents", headers=auth_header(token)).status_code == 403
    assert client.post("/api/consents", json={}, headers=auth_header(token)).status_code == 403
