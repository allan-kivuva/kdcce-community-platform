import pytest


def test_security_headers_present_on_every_response(client):
    resp = client.get("/api/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert resp.headers["Content-Security-Policy"] == "default-src 'none'"
    assert "max-age" in resp.headers["Strict-Transport-Security"]


def test_security_headers_present_on_error_response(client):
    resp = client.get("/api/donations/999999", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_logout_requires_auth(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 401


def test_logout_revokes_access_token(client, make_user, auth_header):
    _, token, _ = make_user()
    # Works once, while the token is still valid.
    resp = client.get("/api/auth/me", headers=auth_header(token))
    assert resp.status_code == 200

    resp = client.post("/api/auth/logout", headers=auth_header(token))
    assert resp.status_code == 204

    # The same token is now rejected everywhere, well before its natural expiry.
    resp = client.get("/api/auth/me", headers=auth_header(token))
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Token has been revoked"


def test_logout_a_second_time_with_the_same_token_is_rejected(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/auth/logout", headers=auth_header(token))
    assert resp.status_code == 204
    # Calling logout again with the now-revoked token hits the blocklist
    # check before the route body ever runs — no risk of a duplicate-jti
    # insert for the access token itself.
    resp = client.post("/api/auth/logout", headers=auth_header(token))
    assert resp.status_code == 401


def test_logout_revokes_refresh_token_when_provided(client, make_user, auth_header):
    _, access_token, refresh_token = make_user()

    resp = client.post(
        "/api/auth/logout",
        headers=auth_header(access_token),
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 204

    resp = client.post("/api/auth/refresh", headers=auth_header(refresh_token))
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Token has been revoked"


def test_logout_ignores_garbage_refresh_token(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post(
        "/api/auth/logout",
        headers=auth_header(access_token),
        json={"refresh_token": "not-a-real-token"},
    )
    assert resp.status_code == 204


def test_logout_ignores_an_access_token_passed_as_refresh_token(client, make_user, auth_header):
    # A caller can't smuggle in another user's access token via the
    # refresh_token field and get it revoked out from under the request's
    # own actor check — decode_token succeeds (it's a real, valid JWT) but
    # its "type" claim is "access", not "refresh", so it's ignored here.
    _, access_token, _ = make_user(email="a@example.com")
    _, other_access_token, _ = make_user(email="b@example.com")
    resp = client.post(
        "/api/auth/logout",
        headers=auth_header(access_token),
        json={"refresh_token": other_access_token},
    )
    assert resp.status_code == 204
    # The other user's access token must still work — it was never revoked.
    resp = client.get("/api/auth/me", headers=auth_header(other_access_token))
    assert resp.status_code == 200


def test_refresh_token_still_works_after_a_different_logout(client, make_user, auth_header):
    _, access_token, refresh_token = make_user()
    # Logging out (revoking only the access token, no refresh_token sent)
    # must not affect the still-unused refresh token.
    client.post("/api/auth/logout", headers=auth_header(access_token))
    resp = client.post("/api/auth/refresh", headers=auth_header(refresh_token))
    assert resp.status_code == 200


def test_donation_public_post_is_rate_limited(client):
    payload = {
        "donor_name": "Amina K.",
        "donor_email": "amina@example.com",
        "amount": 100,
        "frequency": "one-time",
    }
    statuses = [client.post("/api/donations", json=payload).status_code for _ in range(11)]
    assert 429 in statuses
