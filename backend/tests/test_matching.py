from datetime import date, time

from app.extensions import db
from app.models import ElderlyMember, User, VolunteerAvailability, VolunteerProfile, VolunteerUnavailability


def _create_member(admin_token, auth_header, client, full_name="Match Test Member"):
    resp = client.post("/api/elderly", json={"full_name": full_name, "gender": "Female"}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    return resp.get_json()["member"]


def _make_volunteer(email, status="Verified", skills=None, latitude=None, longitude=None):
    user = User(name=email.split("@")[0], email=email, role="volunteer")
    user.set_password("hunter22")
    db.session.add(user)
    db.session.flush()
    profile = VolunteerProfile(user_id=user.id, status=status, skills=skills, latitude=latitude, longitude=longitude)
    db.session.add(profile)
    db.session.commit()
    return user, profile


def test_unverified_volunteer_excluded(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    with app.app_context():
        _make_volunteer("pending-vol@example.com", status="Pending")

    resp = client.get(f"/api/matching/volunteers?member_id={member['id']}", headers=auth_header(token))
    assert resp.status_code == 200
    names = [v["name"] for v in resp.get_json()["volunteers"]]
    assert "pending-vol" not in names


def test_unavailable_volunteer_excluded_for_that_date(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    with app.app_context():
        user, profile = _make_volunteer("away-vol@example.com")
        db.session.add(VolunteerUnavailability(volunteer_profile_id=profile.id, start_date=date(2026, 9, 1), end_date=date(2026, 9, 10), reason="Travel"))
        db.session.commit()

    resp = client.get(f"/api/matching/volunteers?member_id={member['id']}&date=2026-09-05", headers=auth_header(token))
    names = [v["name"] for v in resp.get_json()["volunteers"]]
    assert "away-vol" not in names

    # Outside the unavailable window, the same volunteer IS eligible.
    resp2 = client.get(f"/api/matching/volunteers?member_id={member['id']}&date=2026-09-20", headers=auth_header(token))
    names2 = [v["name"] for v in resp2.get_json()["volunteers"]]
    assert "away-vol" in names2


def test_availability_scoring(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    with app.app_context():
        user, profile = _make_volunteer("available-tue@example.com")
        db.session.add(VolunteerAvailability(volunteer_profile_id=profile.id, day_of_week="Tuesday", start_time=time(9, 0), end_time=time(12, 0)))
        db.session.commit()
        _make_volunteer("no-availability@example.com")

    # 2026-09-01 is a Tuesday.
    resp = client.get(f"/api/matching/volunteers?member_id={member['id']}&date=2026-09-01", headers=auth_header(token))
    results = {v["name"]: v for v in resp.get_json()["volunteers"]}
    assert results["available-tue"]["availability_match"] is True
    assert results["no-availability"]["availability_match"] is False
    assert results["available-tue"]["score"] > results["no-availability"]["score"]
    assert "Available ✓" in results["available-tue"]["reasons"]


def test_skill_scoring(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    with app.app_context():
        _make_volunteer("companionship-skilled@example.com", skills="Companionship, cooking")
        _make_volunteer("no-relevant-skill@example.com", skills="Carpentry")

    resp = client.get(f"/api/matching/volunteers?member_id={member['id']}&request_type=Companionship", headers=auth_header(token))
    results = {v["name"]: v for v in resp.get_json()["volunteers"]}
    assert results["companionship-skilled"]["score"] > results["no-relevant-skill"]["score"]


def test_distance_scoring(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    resp = client.post(
        "/api/elderly", json={"full_name": "Located Member", "gender": "Male"}, headers=auth_header(token),
    )
    member = resp.get_json()["member"]
    with app.app_context():
        m = db.session.get(ElderlyMember, member["id"])
        m.latitude, m.longitude = -1.30, 36.78
        db.session.commit()
        _make_volunteer("nearby@example.com", latitude=-1.301, longitude=36.781)
        _make_volunteer("far-away@example.com", latitude=-1.10, longitude=36.60)
        _make_volunteer("no-location@example.com")

    resp = client.get(f"/api/matching/volunteers?member_id={member['id']}", headers=auth_header(token))
    results = {v["name"]: v for v in resp.get_json()["volunteers"]}
    assert results["nearby"]["distance_km"] is not None
    assert results["far-away"]["distance_km"] is not None
    assert results["nearby"]["distance_km"] < results["far-away"]["distance_km"]
    assert results["nearby"]["score"] > results["far-away"]["score"]
    assert results["no-location"]["distance_km"] is None


def test_workload_scoring(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    other_member = _create_member(token, auth_header, client, full_name="Other Member")
    with app.app_context():
        busy_user, _ = _make_volunteer("busy@example.com")
        idle_user, _ = _make_volunteer("idle@example.com")

    # Give the "busy" volunteer several active home-visit assignments.
    for _ in range(3):
        visit_resp = client.post(
            "/api/home-visits",
            json={"elderly_member_id": other_member["id"], "reason": "Check-in"},
            headers=auth_header(token),
        )
        visit_id = visit_resp.get_json()["visit"]["id"]
        with app.app_context():
            busy = User.query.filter_by(email="busy@example.com").first()
        client.patch(f"/api/home-visits/{visit_id}", json={"assigned_to_id": busy.id, "status": "Assigned"}, headers=auth_header(token))

    resp = client.get(f"/api/matching/volunteers?member_id={member['id']}", headers=auth_header(token))
    results = {v["name"]: v for v in resp.get_json()["volunteers"]}
    assert results["busy"]["workload"] >= 3
    assert results["idle"]["workload"] == 0
    assert results["idle"]["score"] > results["busy"]["score"]


def test_deterministic_ordering(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    with app.app_context():
        _make_volunteer("det-a@example.com")
        _make_volunteer("det-b@example.com")

    resp1 = client.get(f"/api/matching/volunteers?member_id={member['id']}", headers=auth_header(token)).get_json()["volunteers"]
    resp2 = client.get(f"/api/matching/volunteers?member_id={member['id']}", headers=auth_header(token)).get_json()["volunteers"]
    assert [v["volunteer_id"] for v in resp1] == [v["volunteer_id"] for v in resp2]


def test_matching_never_creates_an_assignment(client, make_staff_user, auth_header, app):
    """Purely a recommendation — calling this endpoint must never write
    to HomeVisit/AssistanceRequest."""
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    with app.app_context():
        _make_volunteer("readonly-check@example.com")

    client.get(f"/api/matching/volunteers?member_id={member['id']}", headers=auth_header(token))
    resp = client.get("/api/home-visits", headers=auth_header(token))
    assert resp.get_json()["visits"] == []


def test_matching_admin_staff_only(client, make_staff_user, make_user, auth_header):
    _, staff_token = make_staff_user("staff")
    member = _create_member(staff_token, auth_header, client)

    _, vol_token, _ = make_user()
    assert client.get(f"/api/matching/volunteers?member_id={member['id']}", headers=auth_header(vol_token)).status_code == 403
    assert client.get(f"/api/matching/volunteers?member_id={member['id']}").status_code == 401


def test_matching_requires_member_id(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/matching/volunteers", headers=auth_header(token))
    assert resp.status_code == 400


def test_matching_does_not_expose_private_volunteer_data(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    member = _create_member(token, auth_header, client)
    with app.app_context():
        _make_volunteer("private-check@example.com")

    resp = client.get(f"/api/matching/volunteers?member_id={member['id']}", headers=auth_header(token))
    body_text = resp.get_data(as_text=True)
    assert "private-check@example.com" not in body_text  # email never included, only name
