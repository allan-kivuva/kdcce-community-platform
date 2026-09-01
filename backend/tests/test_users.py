from app.extensions import db
from app.models import AuditLog, User


def test_admin_can_create_staff_user(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post(
        "/api/users",
        json={"name": "New Staffer", "email": "newstaff@example.com", "password": "hunter22", "role": "staff"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    body = resp.get_json()["user"]
    assert body["role"] == "staff"
    assert body["active"] is True
    assert "password" not in body and "password_hash" not in body


def test_admin_can_create_admin_user(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post(
        "/api/users",
        json={"name": "New Admin", "email": "newadmin@example.com", "password": "hunter22", "role": "admin"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.get_json()["user"]["role"] == "admin"


def test_creating_a_volunteer_user_also_creates_a_volunteer_profile(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post(
        "/api/users",
        json={"name": "New Vol", "email": "newvol@example.com", "password": "hunter22", "role": "volunteer"},
        headers=auth_header(token),
    ).get_json()["user"]
    resp = client.get("/api/volunteers", headers=auth_header(token))
    emails = [v["email"] for v in resp.get_json()["volunteers"]]
    assert "newvol@example.com" in emails
    assert created["volunteer_status"] == "Pending"


def test_staff_forbidden_from_creating_users(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post(
        "/api/users",
        json={"name": "Sneaky Staff", "email": "sneaky@example.com", "password": "hunter22", "role": "staff"},
        headers=auth_header(token),
    )
    assert resp.status_code == 403


def test_staff_forbidden_from_creating_admin(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post(
        "/api/users",
        json={"name": "Sneaky", "email": "sneaky2@example.com", "password": "hunter22", "role": "admin"},
        headers=auth_header(token),
    )
    assert resp.status_code == 403


def test_volunteer_forbidden_from_listing_users(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.get("/api/users", headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_users(client):
    assert client.get("/api/users").status_code == 401


def test_duplicate_email_rejected(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    payload = {"name": "Dup", "email": "dup-user@example.com", "password": "hunter22", "role": "staff"}
    assert client.post("/api/users", json=payload, headers=auth_header(token)).status_code == 201
    resp = client.post("/api/users", json=payload, headers=auth_header(token))
    assert resp.status_code == 409


def test_list_users_filters_by_role(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/users", json={"name": "S", "email": "s1@example.com", "password": "hunter22", "role": "staff"}, headers=auth_header(token))
    resp = client.get("/api/users?role=staff", headers=auth_header(token))
    assert resp.status_code == 200
    assert all(u["role"] == "staff" for u in resp.get_json()["users"])


def test_list_users_search_by_name_or_email(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/users", json={"name": "Findable Person", "email": "findme@example.com", "password": "hunter22", "role": "staff"}, headers=auth_header(token))
    resp = client.get("/api/users?q=findable", headers=auth_header(token))
    names = [u["name"] for u in resp.get_json()["users"]]
    assert "Findable Person" in names


def test_role_change_by_admin(client, make_staff_user, auth_header, app):
    admin_user, token = make_staff_user("admin")
    _, staff_token = make_staff_user("staff", email="tobepromoted@example.com")
    with app.app_context():
        target = User.query.filter_by(email="tobepromoted@example.com").first()
        target_id = target.id

    resp = client.patch(f"/api/users/{target_id}/role", json={"role": "admin"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["user"]["role"] == "admin"

    with app.app_context():
        rows = AuditLog.query.filter_by(resource_type="user", resource_id=target_id, action="role_change").all()
        assert len(rows) == 1
        assert rows[0].to_dict()["before"] == {"role": "staff"}
        assert rows[0].to_dict()["after"] == {"role": "admin"}


def test_staff_forbidden_from_changing_roles(client, make_staff_user, auth_header, app):
    _, staff_token = make_staff_user("staff")
    make_staff_user("volunteer", email="target@example.com")
    with app.app_context():
        target_id = User.query.filter_by(email="target@example.com").first().id
    resp = client.patch(f"/api/users/{target_id}/role", json={"role": "admin"}, headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_cannot_demote_the_last_admin(client, make_staff_user, auth_header, app):
    admin_user, token = make_staff_user("admin")
    resp = client.patch(f"/api/users/{admin_user['id']}/role", json={"role": "staff"}, headers=auth_header(token))
    assert resp.status_code == 409
    with app.app_context():
        assert db.session.get(User, admin_user["id"]).role == "admin"


def test_can_demote_an_admin_when_another_admin_remains(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin", email="admin-a@example.com")
    other_admin, _ = make_staff_user("admin", email="admin-b@example.com")
    resp = client.patch(f"/api/users/{other_admin['id']}/role", json={"role": "staff"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["user"]["role"] == "staff"


def test_cannot_deactivate_the_last_admin(client, make_staff_user, auth_header):
    admin_user, token = make_staff_user("admin")
    resp = client.patch(f"/api/users/{admin_user['id']}/status", json={"active": False}, headers=auth_header(token))
    assert resp.status_code == 409


def test_admin_can_deactivate_another_user(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="deactivate-me@example.com")
    resp = client.patch(f"/api/users/{target['id']}/status", json={"active": False}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["user"]["active"] is False

    with app.app_context():
        rows = AuditLog.query.filter_by(resource_type="user", resource_id=target["id"], action="deactivate").all()
        assert len(rows) == 1


def test_disabled_user_cannot_log_in(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    resp = client.post(
        "/api/users",
        json={"name": "Will Be Disabled", "email": "willbedisabled@example.com", "password": "hunter22", "role": "staff"},
        headers=auth_header(admin_token),
    )
    target_id = resp.get_json()["user"]["id"]
    client.patch(f"/api/users/{target_id}/status", json={"active": False}, headers=auth_header(admin_token))

    login_resp = client.post("/api/auth/login", json={"email": "willbedisabled@example.com", "password": "hunter22"})
    assert login_resp.status_code == 403


def test_disabled_users_existing_token_is_rejected_on_next_protected_call(client, make_staff_user, auth_header):
    target, target_token = make_staff_user("staff", email="live-disable@example.com")
    _, admin_token = make_staff_user("admin")

    # Token still works before deactivation.
    assert client.get("/api/donors", headers=auth_header(target_token)).status_code == 200
    client.patch(f"/api/users/{target['id']}/status", json={"active": False}, headers=auth_header(admin_token))
    # Same still-unexpired token is now rejected by the centralized role guard.
    resp = client.get("/api/donors", headers=auth_header(target_token))
    assert resp.status_code == 403


def test_reset_password_returns_a_working_temporary_password(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="resetme@example.com")
    resp = client.post(f"/api/users/{target['id']}/reset-password", headers=auth_header(admin_token))
    assert resp.status_code == 200
    temp_password = resp.get_json()["temporary_password"]
    assert temp_password

    login_resp = client.post("/api/auth/login", json={"email": "resetme@example.com", "password": temp_password})
    assert login_resp.status_code == 200


def test_soft_delete_hides_user_from_default_list_and_blocks_login(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="deleteme@example.com")

    resp = client.delete(f"/api/users/{target['id']}", headers=auth_header(admin_token))
    assert resp.status_code == 204

    listed = client.get("/api/users", headers=auth_header(admin_token)).get_json()["users"]
    assert all(u["id"] != target["id"] for u in listed)

    listed_with_deleted = client.get("/api/users?include_deleted=true", headers=auth_header(admin_token)).get_json()["users"]
    assert any(u["id"] == target["id"] for u in listed_with_deleted)

    login_resp = client.post("/api/auth/login", json={"email": "deleteme@example.com", "password": "hunter22"})
    assert login_resp.status_code == 403


def test_restore_brings_a_soft_deleted_user_back(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    target, _ = make_staff_user("staff", email="restoreme@example.com")
    client.delete(f"/api/users/{target['id']}", headers=auth_header(admin_token))

    resp = client.post(f"/api/users/{target['id']}/restore", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["user"]["active"] is True

    listed = client.get("/api/users", headers=auth_header(admin_token)).get_json()["users"]
    assert any(u["id"] == target["id"] for u in listed)


def test_cannot_soft_delete_the_last_admin(client, make_staff_user, auth_header):
    admin_user, token = make_staff_user("admin")
    resp = client.delete(f"/api/users/{admin_user['id']}", headers=auth_header(token))
    assert resp.status_code == 409


def test_password_hash_never_exposed_in_user_responses(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/users", headers=auth_header(token))
    for user in resp.get_json()["users"]:
        assert "password" not in user and "password_hash" not in user


def test_self_login_history_visible_to_the_user_themselves(client, make_user, auth_header):
    _, token, _ = make_user(email="ownhistory@example.com")
    client.post("/api/auth/login", json={"email": "ownhistory@example.com", "password": "hunter22"})
    resp = client.get("/api/users/me/login-history", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.get_json()["login_history"]) >= 1
    assert all("password" not in entry for entry in resp.get_json()["login_history"])
