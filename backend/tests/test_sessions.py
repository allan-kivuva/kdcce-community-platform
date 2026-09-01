from app.extensions import db
from app.models import AuditLog, User


def _create_user(role="staff", email=None, password="hunter22"):
    email = email or f"{role}@example.com"
    user = User(name="Test User", email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, email, password="hunter22"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    return body["access_token"], body["refresh_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_creates_a_visible_session(client, app):
    _create_user(email="a@example.com")
    access, _ = _login(client, "a@example.com")
    resp = client.get("/api/sessions", headers=_auth(access))
    assert resp.status_code == 200
    sessions = resp.get_json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True
    assert "revoked_at" in sessions[0]


def test_sessions_list_is_scoped_to_the_caller(client, app):
    _create_user(email="a@example.com")
    _create_user(email="b@example.com")
    access_a, _ = _login(client, "a@example.com")
    _login(client, "b@example.com")

    resp = client.get("/api/sessions", headers=_auth(access_a))
    assert len(resp.get_json()["sessions"]) == 1


def test_unauthenticated_cannot_list_sessions(client):
    assert client.get("/api/sessions").status_code == 401


def test_revoke_one_session_blocks_its_refresh_token(client, app):
    _create_user(email="a@example.com")
    access_1, refresh_1 = _login(client, "a@example.com")
    access_2, refresh_2 = _login(client, "a@example.com")

    sessions = client.get("/api/sessions", headers=_auth(access_1)).get_json()["sessions"]
    assert len(sessions) == 2
    other_session = next(s for s in sessions if not s["is_current"])

    resp = client.delete(f"/api/sessions/{other_session['id']}", headers=_auth(access_1))
    assert resp.status_code == 204

    refresh_resp = client.post("/api/auth/refresh", headers=_auth(refresh_2))
    assert refresh_resp.status_code == 401


def test_cannot_revoke_another_users_session_unless_admin(client, app):
    _create_user(role="staff", email="a@example.com")
    _create_user(role="staff", email="b@example.com")
    access_a, _ = _login(client, "a@example.com")
    access_b, _ = _login(client, "b@example.com")

    b_session_id = client.get("/api/sessions", headers=_auth(access_b)).get_json()["sessions"][0]["id"]
    resp = client.delete(f"/api/sessions/{b_session_id}", headers=_auth(access_a))
    assert resp.status_code == 403


def test_admin_can_revoke_another_users_session(client, app):
    _create_user(role="admin", email="admin@example.com")
    _create_user(role="staff", email="b@example.com")
    admin_access, _ = _login(client, "admin@example.com")
    _, b_refresh = _login(client, "b@example.com")

    b_session_id = client.get("/api/sessions?user_id=" + str(User.query.filter_by(email="b@example.com").first().id), headers=_auth(admin_access)).get_json()["sessions"][0]["id"]
    resp = client.delete(f"/api/sessions/{b_session_id}", headers=_auth(admin_access))
    assert resp.status_code == 204

    refresh_resp = client.post("/api/auth/refresh", headers=_auth(b_refresh))
    assert refresh_resp.status_code == 401


def test_revoke_others_keeps_the_current_session_alive(client, app):
    _create_user(email="a@example.com")
    access_1, refresh_1 = _login(client, "a@example.com")
    _access_2, refresh_2 = _login(client, "a@example.com")

    resp = client.post("/api/sessions/revoke-others", headers=_auth(access_1))
    assert resp.status_code == 200
    assert resp.get_json()["revoked_count"] == 1

    # Current session (device 1) still works.
    assert client.post("/api/auth/refresh", headers=_auth(refresh_1)).status_code == 200
    # The other device (device 2) is signed out.
    assert client.post("/api/auth/refresh", headers=_auth(refresh_2)).status_code == 401


def test_revoke_all_signs_out_every_session(client, app):
    _create_user(email="a@example.com")
    access_1, refresh_1 = _login(client, "a@example.com")
    _access_2, refresh_2 = _login(client, "a@example.com")

    resp = client.post("/api/sessions/revoke-all", headers=_auth(access_1))
    assert resp.status_code == 200
    assert resp.get_json()["revoked_count"] == 2

    assert client.post("/api/auth/refresh", headers=_auth(refresh_1)).status_code == 401
    assert client.post("/api/auth/refresh", headers=_auth(refresh_2)).status_code == 401


def test_session_revocation_is_audited(client, app):
    from app.models import AuditLog

    _create_user(email="a@example.com")
    access, _ = _login(client, "a@example.com")
    client.post("/api/sessions/revoke-all", headers=_auth(access))

    rows = AuditLog.query.filter_by(resource_type="session", action="revoke_all").all()
    assert len(rows) == 1


def test_raw_refresh_token_never_appears_in_session_listing(client, app):
    _create_user(email="a@example.com")
    access, refresh = _login(client, "a@example.com")
    resp = client.get("/api/sessions", headers=_auth(access))
    assert refresh not in resp.get_data(as_text=True)
