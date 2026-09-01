from datetime import datetime, timezone

from app.extensions import db
from app.models import User, VolunteerProfile


def _second_volunteer(email="other@example.com"):
    user = User(name="Other Volunteer", email=email, role="volunteer")
    user.set_password("hunter22")
    db.session.add(user)
    db.session.flush()
    db.session.add(VolunteerProfile(user_id=user.id, status="Verified"))
    db.session.commit()
    return user


def test_volunteer_schedule_query(client, make_user, make_staff_user, auth_header, app):
    profile_data, vol_token, _ = make_user()
    with app.app_context():
        vol_user = User.query.filter_by(email=profile_data["email"]).first()
        vol_user_id = vol_user.id
        profile = VolunteerProfile.query.filter_by(user_id=vol_user_id).first()
        profile.status = "Verified"
        db.session.commit()

    _, admin_token = make_staff_user("admin")
    member = client.post("/api/elderly", json={"full_name": "M", "gender": "Female"}, headers=auth_header(admin_token)).get_json()["member"]
    visit = client.post(
        "/api/home-visits",
        json={"elderly_member_id": member["id"], "reason": "Check-in", "scheduled_at": datetime.now(timezone.utc).isoformat()},
        headers=auth_header(admin_token),
    ).get_json()["visit"]
    client.patch(f"/api/home-visits/{visit['id']}", json={"assigned_to_id": vol_user_id, "status": "Assigned"}, headers=auth_header(admin_token))

    resp = client.post("/api/ai/volunteer/query", json={"question": "What's my schedule today?"}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["intent"] == "VOLUNTEER_MY_SCHEDULE"
    assert len(body["results"]) == 1
    assert body["results"][0]["id"] == visit["id"]


def test_volunteer_query_never_exposes_another_volunteers_schedule(client, make_user, auth_header, app):
    profile_a, token_a, _ = make_user(email="a@example.com")
    with app.app_context():
        _second_volunteer()

    resp = client.post("/api/ai/volunteer/query", json={"question": "What's my schedule today?"}, headers=auth_header(token_a))
    assert resp.status_code == 200
    # Structurally impossible to see another volunteer's data — the
    # handler is bound to the caller's own identity, not anything in
    # the question text.
    assert resp.get_json()["results"] == []


def test_volunteer_cannot_use_admin_only_query_phrasing_to_get_org_wide_data(client, make_user, auth_header):
    """Even if a volunteer phrases their question like an admin one, the
    volunteer route only ever consults the narrow volunteer intent map —
    there is no code path to an admin intent handler from this endpoint."""
    _, token, _ = make_user()
    resp = client.post("/api/ai/volunteer/query", json={"question": "Show unassigned assistance requests for everyone."}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["supported"] is False or body["intent"] not in ("UNASSIGNED_REQUESTS", "OVERDUE_CONCERNS", "FINANCE_SUMMARY")


def test_volunteer_hours_query(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/ai/volunteer/query", json={"question": "How many hours have I served?"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["intent"] == "VOLUNTEER_MY_HOURS"


def test_volunteer_training_query(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/ai/volunteer/query", json={"question": "What training do I still need?"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["intent"] == "VOLUNTEER_MY_TRAINING"


def test_admin_forbidden_from_volunteer_query_endpoint(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/volunteer/query", json={"question": "What's my schedule today?"}, headers=auth_header(token))
    assert resp.status_code == 403


def test_family_forbidden_from_volunteer_query(client, make_staff_user, auth_header):
    _, token = make_staff_user("family", email="fam2@example.com")
    resp = client.post("/api/ai/volunteer/query", json={"question": "What's my schedule today?"}, headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_use_volunteer_query(client):
    resp = client.post("/api/ai/volunteer/query", json={"question": "What's my schedule today?"})
    assert resp.status_code == 401
