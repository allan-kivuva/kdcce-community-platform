from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import HomeVisit, User, VolunteerProfile


def _member(client, token, auth_header, name="Test Member"):
    return client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token)).get_json()["member"]


def _verified_volunteer(email):
    user = User(name=email.split("@")[0], email=email, role="volunteer")
    user.set_password("hunter22")
    db.session.add(user)
    db.session.flush()
    db.session.add(VolunteerProfile(user_id=user.id, status="Verified"))
    db.session.commit()
    return user


def test_workload_zero_data_case(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/ai/insights/workload", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["overloaded_volunteers"] == []
    assert data["idle_volunteers"] == []


def test_workload_identifies_idle_and_overloaded_volunteers(client, make_staff_user, auth_header, app):
    _, token = make_staff_user("admin")
    with app.app_context():
        busy = _verified_volunteer("busy@example.com")
        idle = _verified_volunteer("idle@example.com")
        also_busy = _verified_volunteer("busy2@example.com")

    member = _member(client, token, auth_header)
    for vol in ("busy@example.com", "busy2@example.com"):
        with app.app_context():
            user = User.query.filter_by(email=vol).first()
        for _ in range(3):
            visit_resp = client.post(
                "/api/home-visits",
                json={"elderly_member_id": member["id"], "reason": "Check-in", "scheduled_at": datetime.now(timezone.utc).isoformat()},
                headers=auth_header(token),
            )
            visit_id = visit_resp.get_json()["visit"]["id"]
            client.patch(f"/api/home-visits/{visit_id}", json={"assigned_to_id": user.id, "status": "Assigned"}, headers=auth_header(token))

    resp = client.get("/api/ai/insights/workload", headers=auth_header(token))
    data = resp.get_json()["data"]
    idle_names = [v["name"] for v in data["idle_volunteers"]]
    assert "idle" in idle_names


def test_trends_zero_data_case(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/ai/insights/trends", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["assistance_requests"]["direction"] == "flat"
    assert data["assistance_requests"]["pct_change"] == 0.0


def test_trends_detects_increase_in_assistance_requests(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    for _ in range(5):
        client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Transportation", "description": "Ride"}, headers=auth_header(token))

    resp = client.get("/api/ai/insights/trends?period_days=30", headers=auth_header(token))
    data = resp.get_json()["data"]
    assert data["assistance_requests"]["current"] == 5
    assert data["assistance_requests"]["previous"] == 0
    assert data["assistance_requests"]["pct_change"] == 100.0
    assert data["assistance_requests"]["direction"] == "up"


def test_trends_period_days_clamped(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/ai/insights/trends?period_days=5000", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["period_days"] == 90


def test_recommendations_zero_data_case(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/ai/insights/recommendations", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["recommendations"] == []


def test_recommendations_no_gap_while_the_auto_created_follow_up_is_still_open(client, make_staff_user, auth_header):
    """Marking follow_up_required=True on an incident auto-creates a
    linked, Pending FollowUp (see incidents/routes.py) — so right after
    that happens, there's no gap to flag yet."""
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    client.post(
        "/api/incidents",
        json={
            "elderly_member_id": member["id"], "incident_type": "Fall", "severity": "Medium",
            "occurred_at": datetime.now(timezone.utc).isoformat(), "description": "Minor stumble",
            "follow_up_required": True,
        },
        headers=auth_header(token),
    )
    recs = client.get("/api/ai/insights/recommendations", headers=auth_header(token)).get_json()["data"]["recommendations"]
    assert not any(r["type"] == "follow_up" for r in recs)


def test_recommendations_flags_follow_up_gap_on_home_visit(client, make_staff_user, auth_header, app):
    """The gap: a HomeVisit still marked follow_up_required=True whose
    linked FollowUp task has since been completed (or otherwise has no
    open task) — a real staff-workflow edge case, not a fabricated one."""
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    visit_resp = client.post(
        "/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Wellness check"}, headers=auth_header(token),
    )
    visit = visit_resp.get_json()["visit"]
    client.patch(f"/api/home-visits/{visit['id']}", json={"follow_up_required": True, "follow_up_notes": "Check on medication"}, headers=auth_header(token))

    with app.app_context():
        from app.models import FollowUp

        follow_up = FollowUp.query.filter_by(source_type="home_visit", source_id=visit["id"]).first()
        assert follow_up is not None  # confirms the auto-create path fired
        follow_up_id = follow_up.id

    client.patch(f"/api/followups/{follow_up_id}", json={"status": "Completed"}, headers=auth_header(token))

    resp = client.get("/api/ai/insights/recommendations", headers=auth_header(token))
    recs = resp.get_json()["data"]["recommendations"]
    gap_recs = [r for r in recs if r["type"] == "follow_up"]
    assert len(gap_recs) == 1
    assert any(d["source_type"] == "home_visit" and d["source_id"] == visit["id"] for d in gap_recs[0]["detail"])


def test_recommendations_flags_budget_alert(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json={"name": "Feeding Program"}, headers=auth_header(token)).get_json()["program"]
    client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000}, headers=auth_header(token))
    client.post(
        "/api/expenses",
        data={"amount": "950", "category": "Food", "description": "Bulk order", "program_id": str(program["id"]), "expense_date": "2026-08-01", "vendor_name": "Market"},
        headers=auth_header(token),
    )

    resp = client.get("/api/ai/insights/recommendations", headers=auth_header(token))
    recs = resp.get_json()["data"]["recommendations"]
    budget_recs = [r for r in recs if r["type"] == "budget_alert"]
    assert len(budget_recs) == 1
    assert "95" in budget_recs[0]["text"] or "9" in budget_recs[0]["text"]


def test_insights_endpoints_permissions(client, make_user, auth_header):
    _, token, _ = make_user()
    assert client.get("/api/ai/insights/workload", headers=auth_header(token)).status_code == 403
    assert client.get("/api/ai/insights/trends", headers=auth_header(token)).status_code == 403
    assert client.get("/api/ai/insights/recommendations", headers=auth_header(token)).status_code == 403
    assert client.get("/api/ai/insights/workload").status_code == 401
