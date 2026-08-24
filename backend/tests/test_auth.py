def test_register_creates_volunteer_by_default(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Derrick", "email": "derrick@example.com", "password": "hunter22"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["role"] == "volunteer"
    assert body["user"]["email"] == "derrick@example.com"
    assert "access_token" in body and "refresh_token" in body
    assert "password" not in body["user"] and "password_hash" not in body["user"]


def test_register_creates_a_volunteer_profile(client, make_staff_user, auth_header):
    client.post(
        "/api/auth/register",
        json={"name": "Derrick", "email": "derrick2@example.com", "password": "hunter22"},
    )
    _, token = make_staff_user("admin")
    resp = client.get("/api/volunteers", headers=auth_header(token))
    emails = [v["email"] for v in resp.get_json()["volunteers"]]
    assert "derrick2@example.com" in emails


def test_register_rejects_duplicate_email(client, make_user):
    make_user(email="dupe@example.com")
    resp = client.post(
        "/api/auth/register",
        json={"name": "Someone Else", "email": "dupe@example.com", "password": "hunter22"},
    )
    assert resp.status_code == 409


def test_register_rejects_short_password(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "X", "email": "short@example.com", "password": "123"},
    )
    assert resp.status_code == 400
    assert "password" in resp.get_json()["details"]


def test_register_rejects_invalid_email(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "X", "email": "not-an-email", "password": "hunter22"},
    )
    assert resp.status_code == 400


def test_register_rejects_client_supplied_role_field(client):
    # A client can't elevate itself to admin at signup. marshmallow rejects
    # unknown fields by default, so the whole request is refused outright
    # rather than silently dropping "role" — either way, no account is
    # created with a role other than volunteer.
    resp = client.post(
        "/api/auth/register",
        json={"name": "Sneaky", "email": "sneaky@example.com", "password": "hunter22", "role": "admin"},
    )
    assert resp.status_code == 400
    assert client.post(
        "/api/auth/login", json={"email": "sneaky@example.com", "password": "hunter22"}
    ).status_code == 401  # confirm no account was actually created


def test_login_with_correct_credentials(client, make_user):
    make_user(email="ok@example.com", password="correct-horse")
    resp = client.post("/api/auth/login", json={"email": "ok@example.com", "password": "correct-horse"})
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_with_wrong_password(client, make_user):
    make_user(email="ok2@example.com", password="correct-horse")
    resp = client.post("/api/auth/login", json={"email": "ok2@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_with_unknown_email(client):
    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever"})
    assert resp.status_code == 401


def test_me_requires_a_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_rejects_garbage_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage.token.value"})
    assert resp.status_code == 401


def test_me_returns_the_authenticated_user(client, make_user):
    user, access_token, _ = make_user(email="me@example.com")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["id"] == user["id"]


def test_refresh_issues_a_new_access_token(client, make_user):
    _, _, refresh_token = make_user(email="refresh@example.com")
    resp = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_refresh_rejects_an_access_token(client, make_user):
    # Using an access token where a refresh token is required must fail —
    # otherwise a stolen access token could mint itself an indefinite chain.
    _, access_token, _ = make_user(email="refresh2@example.com")
    resp = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 401
