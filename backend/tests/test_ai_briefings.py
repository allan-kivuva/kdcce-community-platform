from datetime import datetime, timezone


def test_admin_briefing_empty_state_says_so_plainly(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/ai/admin/briefing", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["facts"]["today"]["visits_scheduled"] == 0
    assert "Nothing notable" in body["briefing_text"]


def test_admin_briefing_reflects_real_counts_not_invented(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = client.post("/api/elderly", json={"full_name": "M", "gender": "Female"}, headers=auth_header(token)).get_json()["member"]
    client.post(
        "/api/home-visits",
        json={"elderly_member_id": member["id"], "reason": "Check-in", "scheduled_at": datetime.now(timezone.utc).isoformat()},
        headers=auth_header(token),
    )
    client.post(
        "/api/assistance-requests",
        json={"elderly_member_id": member["id"], "request_type": "Transportation", "description": "Ride needed"},
        headers=auth_header(token),
    )

    resp = client.get("/api/ai/admin/briefing", headers=auth_header(token))
    facts = resp.get_json()["facts"]
    assert facts["today"]["visits_scheduled"] == 1
    assert facts["today"]["unassigned_requests"] == 1
    assert "1 home visit(s) scheduled" in resp.get_json()["briefing_text"]


def test_admin_briefing_permissions(client, make_user, auth_header):
    _, token, _ = make_user()
    assert client.get("/api/ai/admin/briefing", headers=auth_header(token)).status_code == 403
    assert client.get("/api/ai/admin/briefing").status_code == 401


def test_volunteer_briefing_empty_state(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.get("/api/ai/volunteer/briefing", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["facts"]["today"]["assignment_count"] == 0
    assert "0.0 hours" in body["briefing_text"]


def test_volunteer_briefing_only_shows_own_data(client, make_user, auth_header, app):
    from app.extensions import db
    from app.models import User, VolunteerProfile

    profile_a, token_a, _ = make_user(email="briefa@example.com")
    with app.app_context():
        other = User(name="Other Vol", email="briefb@example.com", role="volunteer")
        other.set_password("hunter22")
        db.session.add(other)
        db.session.flush()
        db.session.add(VolunteerProfile(user_id=other.id, status="Verified"))
        db.session.commit()

    resp = client.get("/api/ai/volunteer/briefing", headers=auth_header(token_a))
    body_text = resp.get_data(as_text=True)
    assert "Other Vol" not in body_text
    assert "briefb@example.com" not in body_text


def test_volunteer_briefing_permissions(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/ai/volunteer/briefing", headers=auth_header(token))
    assert resp.status_code == 403


def test_briefings_are_audited(client, make_staff_user, auth_header, app):
    from app.models import AIQueryLog

    _, token = make_staff_user("admin")
    client.get("/api/ai/admin/briefing", headers=auth_header(token))
    with app.app_context():
        rows = AIQueryLog.query.filter_by(feature="admin_briefing").all()
        assert len(rows) == 1
        assert rows[0].ai_used is False
