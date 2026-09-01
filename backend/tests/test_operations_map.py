from app.extensions import db
from app.models import ElderlyMember


def _create_geocoded_member(admin_token, auth_header, client, full_name="Map Test Member", status="Active"):
    resp = client.post("/api/elderly", json={"full_name": full_name, "gender": "Female", "location": "Kibera", "status": status}, headers=auth_header(admin_token))
    member = resp.get_json()["member"]
    client.post(f"/api/elderly/{member['id']}/geocode", headers=auth_header(admin_token))
    return member


def test_ungeocoded_members_are_excluded_from_the_map(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/elderly", json={"full_name": "Never Geocoded", "gender": "Male"}, headers=auth_header(token))

    resp = client.get("/api/operations/map?layers=elderly", headers=auth_header(token))
    assert resp.status_code == 200
    names = [p["name"] for p in resp.get_json()["points"]]
    assert "Never Geocoded" not in names


def test_geocoded_member_appears_on_the_elderly_layer(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_geocoded_member(token, auth_header, client)

    resp = client.get("/api/operations/map?layers=elderly", headers=auth_header(token))
    points = resp.get_json()["points"]
    match = next(p for p in points if p["id"] == member["id"] and p["layer"] == "elderly")
    assert match["name"] == "Map Test Member"
    assert match["latitude"] is not None and match["longitude"] is not None


def test_map_popover_excludes_sensitive_fields(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    _create_geocoded_member(token, auth_header, client)

    resp = client.get("/api/operations/map?layers=elderly", headers=auth_header(token))
    body_text = resp.get_data(as_text=True)
    for forbidden in ("health_notes", "vulnerability_notes", "allergies", "dietary_requirements", "emergency_contact"):
        assert forbidden not in body_text


def test_home_visit_layer_shows_status_and_assignee(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _create_geocoded_member(token, auth_header, client)
    visit_resp = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Wellness check"}, headers=auth_header(token))
    visit = visit_resp.get_json()["visit"]

    resp = client.get("/api/operations/map?layers=home_visits", headers=auth_header(token))
    points = resp.get_json()["points"]
    match = next(p for p in points if p["id"] == visit["id"] and p["layer"] == "home_visits")
    assert match["status"] == "Pending"
    assert "reason" not in match
    assert "observations" not in match


def test_status_filter(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    _create_geocoded_member(token, auth_header, client, full_name="Active One", status="Active")
    _create_geocoded_member(token, auth_header, client, full_name="Inactive One", status="Inactive")

    resp = client.get("/api/operations/map?layers=elderly&status=Active", headers=auth_header(token))
    names = [p["name"] for p in resp.get_json()["points"]]
    assert "Active One" in names
    assert "Inactive One" not in names


def test_unknown_layer_rejected(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/operations/map?layers=not_a_real_layer", headers=auth_header(token))
    assert resp.status_code == 400


def test_default_layers_when_none_specified(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/operations/map", headers=auth_header(token))
    assert resp.status_code == 200
    assert set(resp.get_json()["layers"]) == {"elderly", "home_visits", "assistance", "incidents", "volunteers"}


def test_map_admin_staff_only(client, make_staff_user, make_user, auth_header):
    _, staff_token = make_staff_user("staff")
    assert client.get("/api/operations/map", headers=auth_header(staff_token)).status_code == 200

    _, vol_token, _ = make_user()
    assert client.get("/api/operations/map", headers=auth_header(vol_token)).status_code == 403
    assert client.get("/api/operations/map").status_code == 401


def test_family_account_cannot_access_map(client, make_staff_user, auth_header):
    _, family_token = make_staff_user("family", email="mapfam@example.com")
    resp = client.get("/api/operations/map", headers=auth_header(family_token))
    assert resp.status_code == 403


def test_volunteer_with_location_appears_on_volunteer_layer_only_if_verified(client, make_staff_user, make_user, auth_header, app):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="maplocvol@example.com")
    client.patch("/api/volunteers/me", json={"latitude": -1.3, "longitude": 36.8}, headers=auth_header(vol_token))

    # Unverified volunteer (default Pending status) does not appear.
    resp = client.get("/api/operations/map?layers=volunteers", headers=auth_header(admin_token))
    assert resp.get_json()["points"] == []

    with app.app_context():
        from app.models import User, VolunteerProfile

        user = User.query.filter_by(email="maplocvol@example.com").first()
        profile = VolunteerProfile.query.filter_by(user_id=user.id).first()
        profile.status = "Verified"
        db.session.commit()

    resp2 = client.get("/api/operations/map?layers=volunteers", headers=auth_header(admin_token))
    assert len(resp2.get_json()["points"]) == 1
