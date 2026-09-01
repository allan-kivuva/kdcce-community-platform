from app.extensions import db
from app.models import ElderlyMember


def _create_member(admin_token, auth_header, client, location="Kibera, Nairobi"):
    resp = client.post("/api/elderly", json={"full_name": "Geocode Test Member", "gender": "Female", "location": location}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    return resp.get_json()["member"]


def test_geocode_stores_valid_coordinates(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)

    resp = client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["geocoded"] is True
    assert body["member"]["latitude"] is not None
    assert body["member"]["longitude"] is not None
    assert body["member"]["geocode_source"] == "offline"


def test_geocoding_is_deterministic_for_the_same_address(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member_a = _create_member(client=client, admin_token=token, auth_header=auth_header, location="17 Kibera Drive")
    member_b = _create_member(client=client, admin_token=token, auth_header=auth_header, location="17 Kibera Drive")

    resp_a = client.post(f"/api/elderly/{member_a['id']}/geocode", headers=auth_header(token)).get_json()["member"]
    resp_b = client.post(f"/api/elderly/{member_b['id']}/geocode", headers=auth_header(token)).get_json()["member"]
    assert resp_a["latitude"] == resp_b["latitude"]
    assert resp_a["longitude"] == resp_b["longitude"]


def test_unchanged_address_is_not_re_geocoded_without_force(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    first = client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(token)).get_json()
    assert first["geocoded"] is True

    second = client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(token)).get_json()
    assert second["geocoded"] is False
    assert second["cached"] is True


def test_force_re_geocodes(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(token))

    resp = client.post(f"/api/elderly/{member['id']}/geocode?force=true", headers=auth_header(token))
    assert resp.get_json()["geocoded"] is True


def test_geocode_with_no_location_text_fails_cleanly(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/elderly", json={"full_name": "No Location Member", "gender": "Male"}, headers=auth_header(token))
    member = resp.get_json()["member"]

    geocode_resp = client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(token))
    assert geocode_resp.status_code == 400


def test_geocoding_is_audited(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(token))

    resp = client.get(f"/api/audit-logs?resource_type=elderly_member&action=geocode", headers=auth_header(token))
    rows = resp.get_json()["audit_logs"]
    assert len(rows) == 1
    assert rows[0]["resource_id"] == member["id"]


def test_geocode_permissions(client, make_staff_user, make_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)

    _, vol_token, _ = make_user()
    assert client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(vol_token)).status_code == 403
    assert client.post(f"/api/elderly/{member['id']}/geocode").status_code == 401


def test_exact_coordinates_not_included_in_ordinary_member_responses(client, make_staff_user, auth_header):
    """The plain admin elderly-member endpoints must keep returning
    exactly what they did before Phase 8 — latitude/longitude are only
    ever included when a caller explicitly asks (the map endpoint)."""
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(token))

    resp = client.get(f"/api/elderly/{member['id']}", headers=auth_header(token))
    body = resp.get_json()["member"]
    assert "latitude" not in body
    assert "longitude" not in body


def test_volunteer_can_set_own_location_preference(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.patch("/api/volunteers/me", json={"latitude": -1.3, "longitude": 36.8}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["volunteer"]["latitude"] == -1.3
    assert resp.get_json()["volunteer"]["longitude"] == 36.8


def test_volunteer_location_out_of_range_rejected(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.patch("/api/volunteers/me", json={"latitude": 999}, headers=auth_header(token))
    assert resp.status_code == 400
