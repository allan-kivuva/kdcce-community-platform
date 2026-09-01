def test_successful_login_is_recorded(client, make_user, make_staff_user, auth_header):
    make_user(email="ok@example.com", password="correct-horse")
    client.post("/api/auth/login", json={"email": "ok@example.com", "password": "correct-horse"})

    _, admin_token = make_staff_user("admin")
    resp = client.get("/api/login-history?success=true", headers=auth_header(admin_token))
    assert resp.status_code == 200
    rows = resp.get_json()["login_history"]
    assert any(r["attempted_email"] == "ok@example.com" and r["success"] is True for r in rows)


def test_failed_login_is_recorded_with_reason(client, make_user, make_staff_user, auth_header):
    make_user(email="ok2@example.com", password="correct-horse")
    client.post("/api/auth/login", json={"email": "ok2@example.com", "password": "wrong-password"})

    _, admin_token = make_staff_user("admin")
    resp = client.get("/api/login-history?success=false", headers=auth_header(admin_token))
    rows = resp.get_json()["login_history"]
    assert any(r["failure_reason"] == "invalid_credentials" and r["attempted_email"] == "ok2@example.com" for r in rows)


def test_login_history_never_exposes_a_password(client, make_user, make_staff_user, auth_header):
    make_user(email="ok3@example.com", password="correct-horse")
    client.post("/api/auth/login", json={"email": "ok3@example.com", "password": "correct-horse"})

    _, admin_token = make_staff_user("admin")
    resp = client.get("/api/login-history", headers=auth_header(admin_token))
    body_text = resp.get_data(as_text=True)
    assert "correct-horse" not in body_text


def test_unknown_email_login_attempt_recorded_without_a_user_id(client, make_staff_user, auth_header):
    client.post("/api/auth/login", json={"email": "nobody-at-all@example.com", "password": "whatever"})
    _, admin_token = make_staff_user("admin")
    resp = client.get("/api/login-history", headers=auth_header(admin_token))
    rows = resp.get_json()["login_history"]
    match = next(r for r in rows if r["attempted_email"] == "nobody-at-all@example.com")
    assert match["user_id"] is None
    assert match["success"] is False


def test_staff_forbidden_from_full_login_history(client, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    resp = client.get("/api/login-history", headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_volunteer_forbidden_from_full_login_history(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.get("/api/login-history", headers=auth_header(token))
    assert resp.status_code == 403


def test_user_can_see_their_own_login_history(client, make_user, auth_header):
    _, token, _ = make_user(email="self@example.com", password="hunter22")
    client.post("/api/auth/login", json={"email": "self@example.com", "password": "hunter22"})
    resp = client.get("/api/users/me/login-history", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.get_json()["login_history"]) >= 1


def test_user_cannot_see_someone_elses_login_history_via_self_endpoint(client, make_user):
    _, token_a, _ = make_user(email="a2@example.com", password="hunter22")
    _, _token_b, _ = make_user(email="b2@example.com", password="hunter22")
    client.post("/api/auth/login", json={"email": "b2@example.com", "password": "hunter22"})

    resp = client.get("/api/users/me/login-history", headers={"Authorization": f"Bearer {token_a}"})
    rows = resp.get_json()["login_history"]
    assert all("b2@example.com" not in str(row) for row in rows)


def test_account_disabled_rejection_is_recorded(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post(
        "/api/users",
        json={"name": "Disabled", "email": "disabled-login@example.com", "password": "hunter22", "role": "staff"},
        headers=auth_header(admin_token),
    ).get_json()["user"]
    client.patch(f"/api/users/{created['id']}/status", json={"active": False}, headers=auth_header(admin_token))

    client.post("/api/auth/login", json={"email": "disabled-login@example.com", "password": "hunter22"})
    resp = client.get("/api/login-history?success=false", headers=auth_header(admin_token))
    rows = resp.get_json()["login_history"]
    assert any(r["failure_reason"] == "account_disabled" for r in rows)
