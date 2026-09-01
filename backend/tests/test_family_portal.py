from app.extensions import db
from app.models import Consent, ElderlyMember, FamilyMemberAccess


def _create_member(admin_token, auth_header, client, full_name="Test Member", health_notes="Diabetic, needs insulin"):
    resp = client.post(
        "/api/elderly",
        json={"full_name": full_name, "gender": "Female", "health_notes": health_notes, "vulnerability_notes": "Lives alone"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["member"]


def _create_family_user(admin_token, auth_header, client, email="family1@example.com"):
    resp = client.post(
        "/api/users",
        json={"name": "Family One", "email": email, "password": "hunter22", "role": "family"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["user"]


def _link_and_approve(admin_token, auth_header, client, user_id, member_id, relationship="Daughter"):
    created = client.post(
        "/api/admin/family-access",
        json={"user_id": user_id, "elderly_member_id": member_id, "relationship": relationship},
        headers=auth_header(admin_token),
    ).get_json()["family_access"]
    approved = client.patch(f"/api/admin/family-access/{created['id']}/approve", headers=auth_header(admin_token)).get_json()["family_access"]
    return approved


def _grant_portal_consent(admin_token, auth_header, client, member_id):
    resp = client.post(
        "/api/consents",
        json={"elderly_member_id": member_id, "consent_type": "Family Portal Access", "status": "Granted"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["consent"]


def _fully_authorized_family_login(client, make_staff_user, auth_header, email="family1@example.com"):
    """Full happy-path setup: family user linked, approved, and with
    Family Portal Access consent granted — used as the baseline for
    tests that need a genuinely working access path before breaking one
    specific piece of it."""
    _, admin_token = make_staff_user("admin")
    member = _create_member(admin_token, auth_header, client)
    family_user, family_token = make_staff_user("family", email=email)
    _link_and_approve(admin_token, auth_header, client, family_user["id"], member["id"])
    _grant_portal_consent(admin_token, auth_header, client, member["id"])
    return admin_token, member, family_user, family_token


def test_family_user_sees_only_authorized_members(client, make_staff_user, auth_header):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    other_member = _create_member(admin_token, auth_header, client, full_name="Unrelated Person")

    resp = client.get("/api/family/members", headers=auth_header(family_token))
    assert resp.status_code == 200
    members = resp.get_json()["members"]
    assert len(members) == 1
    assert members[0]["id"] == member["id"]
    assert all(m["id"] != other_member["id"] for m in members)


def test_arbitrary_member_id_attack_returns_404(client, make_staff_user, auth_header):
    """The Phase 8 brief's own worked example: a family user authorized
    for one member requests a DIFFERENT, real member's data by ID."""
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    other_member = _create_member(admin_token, auth_header, client, full_name="Someone Else Entirely")

    resp = client.get(f"/api/family/members/{other_member['id']}", headers=auth_header(family_token))
    assert resp.status_code == 404


def test_nonexistent_member_id_returns_the_same_response_as_unauthorized(client, make_staff_user, auth_header):
    """Never leak whether an unauthorized member ID exists at all — a
    real-but-unauthorized member and a member ID that doesn't exist at
    all must produce an identical response."""
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    other_member = _create_member(admin_token, auth_header, client, full_name="Someone Else")

    resp_unauthorized = client.get(f"/api/family/members/{other_member['id']}", headers=auth_header(family_token))
    resp_nonexistent = client.get("/api/family/members/999999", headers=auth_header(family_token))

    assert resp_unauthorized.status_code == resp_nonexistent.status_code == 404
    assert resp_unauthorized.get_json() == resp_nonexistent.get_json()


def test_revoked_access_blocks_immediately(client, make_staff_user, auth_header):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)

    # Works before revocation.
    assert client.get(f"/api/family/members/{member['id']}", headers=auth_header(family_token)).status_code == 200

    access_row = client.get(f"/api/admin/family-access?user_id={family_user['id']}", headers=auth_header(admin_token)).get_json()["family_access"][0]
    client.patch(f"/api/admin/family-access/{access_row['id']}/revoke", headers=auth_header(admin_token))

    resp = client.get(f"/api/family/members/{member['id']}", headers=auth_header(family_token))
    assert resp.status_code == 404


def test_suspended_access_blocks(client, make_staff_user, auth_header):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    access_row = client.get(f"/api/admin/family-access?user_id={family_user['id']}", headers=auth_header(admin_token)).get_json()["family_access"][0]
    client.patch(f"/api/admin/family-access/{access_row['id']}/suspend", headers=auth_header(admin_token))

    resp = client.get(f"/api/family/members/{member['id']}", headers=auth_header(family_token))
    assert resp.status_code == 404


def test_pending_access_does_not_grant_access(client, make_staff_user, auth_header):
    """Only Active access grants anything — a freshly created (Pending),
    unapproved relationship must not work yet."""
    _, admin_token = make_staff_user("admin")
    member = _create_member(admin_token, auth_header, client)
    family_user, family_token = make_staff_user("family", email="pendingfam@example.com")
    client.post(
        "/api/admin/family-access",
        json={"user_id": family_user["id"], "elderly_member_id": member["id"], "relationship": "Son"},
        headers=auth_header(admin_token),
    )
    _grant_portal_consent(admin_token, auth_header, client, member["id"])

    resp = client.get(f"/api/family/members/{member['id']}", headers=auth_header(family_token))
    assert resp.status_code == 404


def test_consent_withdrawal_blocks_access_even_with_active_relationship(client, make_staff_user, auth_header):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    assert client.get(f"/api/family/members/{member['id']}", headers=auth_header(family_token)).status_code == 200

    client.post(
        "/api/consents",
        json={"elderly_member_id": member["id"], "consent_type": "Family Portal Access", "status": "Withdrawn"},
        headers=auth_header(admin_token),
    )

    resp = client.get(f"/api/family/members/{member['id']}", headers=auth_header(family_token))
    assert resp.status_code == 404


def test_family_visible_member_fields_exclude_sensitive_data(client, make_staff_user, auth_header):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    resp = client.get(f"/api/family/members/{member['id']}", headers=auth_header(family_token))
    body = resp.get_json()["member"]

    for forbidden_field in ("health_notes", "vulnerability_notes", "allergies", "dietary_requirements", "emergency_contact_phone", "location", "latitude", "longitude", "date_of_birth"):
        assert forbidden_field not in body

    raw_text = resp.get_data(as_text=True)
    assert "Diabetic" not in raw_text
    assert "Lives alone" not in raw_text


def test_family_cannot_browse_the_full_elderly_roster(client, make_staff_user, auth_header):
    _, _, _, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    resp = client.get("/api/elderly", headers=auth_header(family_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_reach_family_endpoints(client):
    assert client.get("/api/family/members").status_code == 401
    assert client.get("/api/family/members/1").status_code == 401


def test_volunteer_cannot_reach_family_endpoints(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.get("/api/family/members", headers=auth_header(token))
    assert resp.status_code == 403


def test_admin_can_manage_the_full_family_access_lifecycle(client, make_staff_user, auth_header, app):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)

    with app.app_context():
        row = FamilyMemberAccess.query.filter_by(user_id=family_user["id"], elderly_member_id=member["id"]).first()
        assert row.access_status == "Active"
        assert row.approved_by_id is not None
        assert row.approved_at is not None


def test_staff_can_manage_but_volunteer_is_forbidden_from_family_access(client, make_staff_user, make_user, auth_header):
    _, staff_token = make_staff_user("staff")
    resp = client.get("/api/admin/family-access", headers=auth_header(staff_token))
    assert resp.status_code == 200  # staff IS allowed to manage (see roles_required("admin", "staff"))

    _, vol_token, _ = make_user()
    resp = client.get("/api/admin/family-access", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_cannot_link_a_non_family_role_account(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _create_member(admin_token, auth_header, client)
    staff_user, _ = make_staff_user("staff", email="notfamily@example.com")

    resp = client.post(
        "/api/admin/family-access",
        json={"user_id": staff_user["id"], "elderly_member_id": member["id"], "relationship": "Friend"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 400


def test_duplicate_relationship_rejected(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _create_member(admin_token, auth_header, client)
    family_user, _ = make_staff_user("family", email="dupfam@example.com")

    payload = {"user_id": family_user["id"], "elderly_member_id": member["id"], "relationship": "Son"}
    assert client.post("/api/admin/family-access", json=payload, headers=auth_header(admin_token)).status_code == 201
    resp = client.post("/api/admin/family-access", json=payload, headers=auth_header(admin_token))
    assert resp.status_code == 409


def test_family_access_changes_are_audited(client, make_staff_user, auth_header, app):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    resp = client.get(f"/api/audit-logs?resource_type=family_access", headers=auth_header(admin_token))
    actions = [row["action"] for row in resp.get_json()["audit_logs"]]
    assert "create" in actions
    assert "approve" in actions


def test_visits_endpoint_excludes_observations_and_staff_notes(client, make_staff_user, auth_header):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    resp = client.get(f"/api/family/members/{member['id']}/visits", headers=auth_header(family_token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert "visits" in body and "assistance_requests" in body
    for visit in body["visits"]:
        assert "observations" not in visit
        assert "support_provided" not in visit
        assert "staff_notes" not in visit
        assert "reason" not in visit


def test_updates_endpoint_reachable_and_authorized(client, make_staff_user, auth_header):
    _, member, _, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    resp = client.get(f"/api/family/members/{member['id']}/updates", headers=auth_header(family_token))
    assert resp.status_code == 200
    assert "updates" in resp.get_json()


def test_programs_endpoint_reachable_and_authorized(client, make_staff_user, auth_header):
    _, member, _, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    resp = client.get(f"/api/family/members/{member['id']}/programs", headers=auth_header(family_token))
    assert resp.status_code == 200
    assert "activities" in resp.get_json()


# ---------- Family messaging ----------

def test_family_can_message_admin_staff_only(client, make_staff_user, auth_header):
    _, _, _, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    resp = client.get("/api/messages/recipients", headers=auth_header(family_token))
    assert resp.status_code == 200
    roles_seen = {r["role"] for r in resp.get_json()["recipients"]}
    assert roles_seen <= {"admin", "staff"}


def test_family_cannot_message_a_volunteer_directly(client, make_staff_user, make_user, auth_header):
    _, _, _, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    _, _, _ = make_user(email="somevol@example.com")
    from app.models import User
    from app.extensions import db as _db

    volunteer = User.query.filter_by(email="somevol@example.com").first()
    resp = client.post(
        "/api/messages/conversations", json={"recipient_id": volunteer.id, "body": "Hi"}, headers=auth_header(family_token),
    )
    assert resp.status_code == 400


def test_family_message_about_authorized_member_is_tagged(client, make_staff_user, auth_header, app):
    from app.models import Conversation, User

    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    admin_user_id = User.query.filter_by(role="admin").first().id

    resp = client.post(
        "/api/messages/conversations",
        json={"recipient_id": admin_user_id, "body": "How is mum doing?", "elderly_member_id": member["id"]},
        headers=auth_header(family_token),
    )
    assert resp.status_code == 201
    conversation_id = resp.get_json()["conversation"]["id"]

    with app.app_context():
        row = db.session.get(Conversation, conversation_id)
        assert row.elderly_member_id == member["id"]


def test_family_message_about_unauthorized_member_is_rejected(client, make_staff_user, auth_header):
    admin_token, member, family_user, family_token = _fully_authorized_family_login(client, make_staff_user, auth_header)
    other_member = _create_member(admin_token, auth_header, client, full_name="Not Yours")

    from app.models import User

    admin_user_id = User.query.filter_by(role="admin").first().id
    resp = client.post(
        "/api/messages/conversations",
        json={"recipient_id": admin_user_id, "body": "About someone else", "elderly_member_id": other_member["id"]},
        headers=auth_header(family_token),
    )
    assert resp.status_code == 400
