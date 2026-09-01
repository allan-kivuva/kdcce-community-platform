def _program(client, token, auth_header, name="Feeding Program"):
    return client.post("/api/programs", json={"name": name, "status": "Active"}, headers=auth_header(token)).get_json()["program"]


def _expense(client, token, auth_header, amount, program_id, expense_date="2026-01-15", status=None):
    resp = client.post("/api/expenses", data={"amount": str(amount), "category": "Food", "expense_date": expense_date, "program_id": str(program_id)}, content_type="multipart/form-data", headers=auth_header(token))
    expense = resp.get_json()["expense"]
    if status:
        client.patch(f"/api/expenses/{expense['id']}", json={"status": status}, headers=auth_header(token))
    return expense


def test_admin_can_create_budget(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    resp = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 300000}, headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["budget"]
    assert body["allocated_amount"] == 300000.0
    assert body["spent"] == 0
    assert body["remaining"] == 300000.0


def test_volunteer_cannot_create_budget(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    program = _program(client, admin_token, auth_header)
    _, vol_token, _ = make_user()
    resp = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_budget_rejects_unknown_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/budgets", json={"program_id": 999999, "allocated_amount": 1000}, headers=auth_header(token))
    assert resp.status_code == 400


def test_budget_rejects_negative_allocation(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    resp = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": -5}, headers=auth_header(token))
    assert resp.status_code == 400


def test_budget_rejects_end_before_start(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    resp = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000, "period_start": "2026-06-01", "period_end": "2026-01-01"}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Spent / remaining calculation ----------

def test_spent_sums_recorded_and_approved_expenses(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    budget = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000}, headers=auth_header(token)).get_json()["budget"]

    _expense(client, token, auth_header, 200, program["id"])  # Recorded
    _expense(client, token, auth_header, 300, program["id"], status="Approved")

    resp = client.get(f"/api/budgets/{budget['id']}", headers=auth_header(token))
    body = resp.get_json()["budget"]
    assert body["spent"] == 500
    assert body["remaining"] == 500


def test_spent_excludes_rejected_and_voided_expenses(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    budget = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000}, headers=auth_header(token)).get_json()["budget"]

    _expense(client, token, auth_header, 200, program["id"], status="Rejected")
    _expense(client, token, auth_header, 300, program["id"], status="Voided")
    _expense(client, token, auth_header, 100, program["id"])  # counts

    resp = client.get(f"/api/budgets/{budget['id']}", headers=auth_header(token))
    assert resp.get_json()["budget"]["spent"] == 100


def test_spent_excludes_expenses_outside_budget_period(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    budget = client.post("/api/budgets", json={
        "program_id": program["id"], "allocated_amount": 1000, "period_start": "2026-01-01", "period_end": "2026-01-31",
    }, headers=auth_header(token)).get_json()["budget"]

    _expense(client, token, auth_header, 200, program["id"], expense_date="2026-01-15")  # in period
    _expense(client, token, auth_header, 500, program["id"], expense_date="2026-03-01")  # outside period

    resp = client.get(f"/api/budgets/{budget['id']}", headers=auth_header(token))
    assert resp.get_json()["budget"]["spent"] == 200


def test_spent_excludes_expenses_from_other_programs(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header, "Feeding")
    other_program = _program(client, token, auth_header, "Health")
    budget = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000}, headers=auth_header(token)).get_json()["budget"]

    _expense(client, token, auth_header, 400, other_program["id"])

    resp = client.get(f"/api/budgets/{budget['id']}", headers=auth_header(token))
    assert resp.get_json()["budget"]["spent"] == 0


# ---------- Warning levels ----------

def test_warning_level_at_75_percent(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    budget = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000}, headers=auth_header(token)).get_json()["budget"]
    _expense(client, token, auth_header, 750, program["id"])
    resp = client.get(f"/api/budgets/{budget['id']}", headers=auth_header(token))
    assert resp.get_json()["budget"]["warning_level"] == "warning"


def test_warning_level_exceeded(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    budget = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000}, headers=auth_header(token)).get_json()["budget"]
    _expense(client, token, auth_header, 1200, program["id"])
    resp = client.get(f"/api/budgets/{budget['id']}", headers=auth_header(token))
    assert resp.get_json()["budget"]["warning_level"] == "exceeded"


def test_recording_an_expense_over_budget_is_not_blocked(client, make_staff_user, auth_header):
    """Warnings are informational only — recording an over-budget expense
    must still succeed."""
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 100}, headers=auth_header(token))
    expense = _expense(client, token, auth_header, 5000, program["id"])
    assert expense["status"] == "Recorded"


def test_no_warning_under_threshold(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    budget = client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 1000}, headers=auth_header(token)).get_json()["budget"]
    _expense(client, token, auth_header, 100, program["id"])
    resp = client.get(f"/api/budgets/{budget['id']}", headers=auth_header(token))
    assert resp.get_json()["budget"]["warning_level"] is None


def test_unauthenticated_cannot_list_budgets(client):
    assert client.get("/api/budgets").status_code == 401
