from datetime import date, datetime, timedelta, timezone

from app.extensions import db
from app.models import AssistanceRequest, ElderlyMember, HomeVisit, Incident


def _member(client, token, auth_header, name="Test Member"):
    return client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token)).get_json()["member"]


def test_visits_today_intent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    client.post("/api/home-visits", json={"elderly_member_id": member["id"], "reason": "Check-in", "scheduled_at": datetime.now(timezone.utc).isoformat()}, headers=auth_header(token))

    resp = client.post("/api/ai/admin/query", json={"question": "How many visits are scheduled today?"}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["supported"] is True
    assert body["intent"] == "VISITS_TODAY"
    assert len(body["results"]) == 1
    assert "1" in body["answer"]


def test_unassigned_requests_intent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    client.post("/api/assistance-requests", json={"elderly_member_id": member["id"], "request_type": "Transportation", "description": "Needs a ride"}, headers=auth_header(token))

    resp = client.post("/api/ai/admin/query", json={"question": "Show unassigned assistance requests."}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["intent"] == "UNASSIGNED_REQUESTS"
    assert len(body["results"]) == 1


def test_unsupported_question_returns_helpful_fallback(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/admin/query", json={"question": "What is the airspeed velocity of an unladen swallow?"}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["supported"] is False
    assert "examples" in body and len(body["examples"]) > 0


def test_empty_question_rejected(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/admin/query", json={"question": ""}, headers=auth_header(token))
    assert resp.status_code == 400


def test_oversized_question_rejected(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/admin/query", json={"question": "x" * 5000}, headers=auth_header(token))
    assert resp.status_code == 400


def test_inventory_low_stock_intent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    item = client.post("/api/inventory", json={"name": "Rice", "unit": "kg", "minimum_stock": 20}, headers=auth_header(token)).get_json()["item"]
    client.post(f"/api/inventory/{item['id']}/movements", json={"movement_type": "In", "quantity": 5}, headers=auth_header(token))

    resp = client.post("/api/ai/admin/query", json={"question": "What items are running low on stock?"}, headers=auth_header(token))
    body = resp.get_json()
    assert body["intent"] == "INVENTORY_LOW_STOCK"
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "Rice"


def test_members_without_recent_visits_intent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    _member(client, token, auth_header, "Never Visited")

    resp = client.post("/api/ai/admin/query", json={"question": "Which elderly members have not received a home visit in 30 days?"}, headers=auth_header(token))
    body = resp.get_json()
    assert body["intent"] == "MEMBERS_WITHOUT_RECENT_VISITS"
    assert any(r["member_name"] == "Never Visited" for r in body["results"])


def test_high_priority_concerns_intent_excludes_low_severity(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    client.post("/api/incidents", json={"elderly_member_id": member["id"], "incident_type": "Fall", "severity": "Critical", "occurred_at": datetime.now(timezone.utc).isoformat(), "description": "Serious fall"}, headers=auth_header(token))
    client.post("/api/incidents", json={"elderly_member_id": member["id"], "incident_type": "Other", "severity": "Low", "occurred_at": datetime.now(timezone.utc).isoformat(), "description": "Minor issue"}, headers=auth_header(token))

    resp = client.post("/api/ai/admin/query", json={"question": "Show unresolved high-priority concerns."}, headers=auth_header(token))
    body = resp.get_json()
    assert body["intent"] == "OVERDUE_CONCERNS"
    assert len(body["results"]) == 1
    assert body["results"][0]["severity"] == "Critical"


def test_low_stock_inventory_query_variant(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/admin/query", json={"question": "inventory low stock"}, headers=auth_header(token))
    assert resp.get_json()["intent"] == "INVENTORY_LOW_STOCK"


def test_campaigns_below_threshold_intent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/campaigns", json={"name": "Water Wells", "goal_amount": 10000, "status": "Active"}, headers=auth_header(token))

    resp = client.post("/api/ai/admin/query", json={"question": "Show campaigns below 50% of their goal."}, headers=auth_header(token))
    body = resp.get_json()
    assert body["intent"] == "CAMPAIGNS_BELOW_THRESHOLD"
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "Water Wells"


def test_finance_summary_intent_for_a_named_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json={"name": "Feeding Program"}, headers=auth_header(token)).get_json()["program"]
    client.post(
        "/api/expenses", data={"amount": "500", "category": "Food", "description": "Groceries", "program_id": str(program["id"]), "expense_date": date.today().isoformat(), "vendor_name": "Local Market"},
        headers=auth_header(token),
    )

    resp = client.post("/api/ai/admin/query", json={"question": "How much has the Feeding Program spent this month?"}, headers=auth_header(token))
    body = resp.get_json()
    assert body["intent"] == "FINANCE_SUMMARY"
    assert "500" in body["answer"]


def test_finance_summary_unknown_program_reports_clearly(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/admin/query", json={"question": "How much has the Nonexistent Program spent?"}, headers=auth_header(token))
    body = resp.get_json()
    assert body["results"] == []


def test_deterministic_query_correctness_is_source_of_truth_not_ai_prose(client, make_staff_user, auth_header):
    """The `answer` field must always be the exact deterministic figure —
    ai_explanation may vary/rephrase, but `answer` never does."""
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/admin/query", json={"question": "How many visits are scheduled today?"}, headers=auth_header(token))
    body = resp.get_json()
    assert body["answer"] == "No home visits are scheduled today."
    assert body["ai_used"] is False
    assert body["ai_explanation"] == body["answer"]  # deterministic fallback used verbatim


def test_staff_can_use_admin_query(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/ai/admin/query", json={"question": "How many visits are scheduled today?"}, headers=auth_header(token))
    assert resp.status_code == 200


def test_volunteer_forbidden_from_admin_query(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/ai/admin/query", json={"question": "How many visits are scheduled today?"}, headers=auth_header(token))
    assert resp.status_code == 403


def test_family_forbidden_from_admin_query(client, make_staff_user, auth_header):
    _, token = make_staff_user("family", email="fam@example.com")
    resp = client.post("/api/ai/admin/query", json={"question": "How many visits are scheduled today?"}, headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_use_admin_query(client):
    resp = client.post("/api/ai/admin/query", json={"question": "How many visits are scheduled today?"})
    assert resp.status_code == 401


def test_ai_status_reports_disabled_by_default(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.get("/api/ai/admin/status", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["ai_enabled"] is False
