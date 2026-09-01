def _program(client, token, auth_header, name="Feeding"):
    return client.post("/api/programs", json={"name": name, "status": "Active"}, headers=auth_header(token)).get_json()["program"]


def test_donations_report_includes_by_campaign(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    campaign = client.post("/api/admin/campaigns", json={"name": "Water Wells", "goal_amount": 1000}, headers=auth_header(token)).get_json()["campaign"]
    client.post("/api/donations", json={"donor_name": "A", "donor_email": "a@example.com", "amount": 200, "frequency": "one-time", "campaign": "Water Wells"})

    resp = client.get("/api/reports/donations", headers=auth_header(token))
    assert resp.status_code == 200
    by_campaign = resp.get_json()["report"]["by_campaign"]
    assert any(row["campaign"] == "Water Wells" and row["amount"] == 200 for row in by_campaign)


def test_volunteer_cannot_access_donations_report(client, make_user, auth_header):
    _, token, _ = make_user()
    assert client.get("/api/reports/donations", headers=auth_header(token)).status_code == 403


# ---------- Campaigns report ----------

def test_campaigns_report_shows_raised_vs_goal(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    campaign = client.post("/api/admin/campaigns", json={"name": "Big Drive", "goal_amount": 1000}, headers=auth_header(token)).get_json()["campaign"]
    d = client.post("/api/donations", json={"donor_name": "A", "donor_email": "a2@example.com", "amount": 300, "frequency": "one-time"}).get_json()["donation"]
    client.patch(f"/api/donations/{d['id']}", json={"campaign_id": campaign["id"]}, headers=auth_header(token))

    resp = client.get("/api/reports/campaigns", headers=auth_header(token))
    assert resp.status_code == 200
    report = resp.get_json()["report"]
    row = next(r for r in report["campaigns"] if r["id"] == campaign["id"])
    assert row["raised_amount"] == 300
    assert row["goal_amount"] == 1000


def test_volunteer_cannot_access_campaigns_report(client, make_user, auth_header):
    _, token, _ = make_user()
    assert client.get("/api/reports/campaigns", headers=auth_header(token)).status_code == 403


# ---------- Expenses report ----------

def test_expenses_report_totals_and_by_category(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    client.post("/api/expenses", data={"amount": "100", "category": "Food", "expense_date": "2026-01-10", "program_id": str(program["id"])}, content_type="multipart/form-data", headers=auth_header(token))
    client.post("/api/expenses", data={"amount": "50", "category": "Transport", "expense_date": "2026-01-11", "program_id": str(program["id"])}, content_type="multipart/form-data", headers=auth_header(token))

    resp = client.get("/api/reports/expenses", headers=auth_header(token))
    assert resp.status_code == 200
    report = resp.get_json()["report"]
    assert report["total_amount"] == 150
    categories = {row["category"]: row["amount"] for row in report["by_category"]}
    assert categories["Food"] == 100
    assert categories["Transport"] == 50
    assert any(row["program_name"] == program["name"] for row in report["by_program"])


def test_expenses_report_excludes_voided(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header)
    created = client.post("/api/expenses", data={"amount": "500", "category": "Food", "expense_date": "2026-01-10", "program_id": str(program["id"])}, content_type="multipart/form-data", headers=auth_header(token)).get_json()["expense"]
    client.patch(f"/api/expenses/{created['id']}", json={"status": "Voided"}, headers=auth_header(token))

    resp = client.get("/api/reports/expenses", headers=auth_header(token))
    assert resp.get_json()["report"]["total_amount"] == 0


def test_expenses_csv_export(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/expenses", data={"amount": "75", "category": "Medical", "expense_date": "2026-01-10"}, content_type="multipart/form-data", headers=auth_header(token))
    resp = client.get("/api/reports/expenses/export.csv", headers=auth_header(token))
    assert resp.status_code == 200
    assert b"Medical" in resp.data


def test_volunteer_cannot_access_expenses_report(client, make_user, auth_header):
    _, token, _ = make_user()
    assert client.get("/api/reports/expenses", headers=auth_header(token)).status_code == 403


# ---------- Budgets report ----------

def test_budgets_report_flags_over_budget_programs(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = _program(client, token, auth_header, "Health")
    client.post("/api/budgets", json={"program_id": program["id"], "allocated_amount": 100}, headers=auth_header(token))
    client.post("/api/expenses", data={"amount": "500", "category": "Medical", "expense_date": "2026-01-10", "program_id": str(program["id"])}, content_type="multipart/form-data", headers=auth_header(token))

    resp = client.get("/api/reports/budgets", headers=auth_header(token))
    assert resp.status_code == 200
    over = resp.get_json()["report"]["over_budget_programs"]
    assert any(row["program_name"] == "Health" for row in over)


def test_volunteer_cannot_access_budgets_report(client, make_user, auth_header):
    _, token, _ = make_user()
    assert client.get("/api/reports/budgets", headers=auth_header(token)).status_code == 403


# ---------- Donors report ----------

def test_donors_report_counts_repeat_donors(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/donations", json={"donor_name": "Repeat", "donor_email": "repeatrep@example.com", "amount": 100, "frequency": "one-time"})
    client.post("/api/donations", json={"donor_name": "Repeat", "donor_email": "repeatrep@example.com", "amount": 200, "frequency": "one-time"})
    client.post("/api/donations", json={"donor_name": "OneTime", "donor_email": "onetimerep@example.com", "amount": 50, "frequency": "one-time"})

    resp = client.get("/api/reports/donors", headers=auth_header(token))
    assert resp.status_code == 200
    report = resp.get_json()["report"]
    assert report["repeat_donors"] >= 1
    assert any(d["lifetime_amount"] == 300 for d in report["top_donors"])


def test_volunteer_cannot_access_donors_report(client, make_user, auth_header):
    _, token, _ = make_user()
    assert client.get("/api/reports/donors", headers=auth_header(token)).status_code == 403


# ---------- Audit logging ----------

def test_donor_creation_is_audited(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post("/api/donors", json={"name": "Audited Donor"}, headers=auth_header(token)).get_json()["donor"]
    resp = client.get(f"/api/audit-logs?resource_type=donor&resource_id={created['id']}", headers=auth_header(token))
    assert resp.status_code == 200
    logs = resp.get_json()["audit_logs"]
    assert any(l["action"] == "create" for l in logs)


def test_campaign_status_change_is_audited(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    campaign = client.post("/api/admin/campaigns", json={"name": "Audited Campaign", "goal_amount": 1000}, headers=auth_header(token)).get_json()["campaign"]
    client.patch(f"/api/admin/campaigns/{campaign['id']}", json={"status": "Paused"}, headers=auth_header(token))

    resp = client.get(f"/api/audit-logs?resource_type=campaign&resource_id={campaign['id']}", headers=auth_header(token))
    logs = resp.get_json()["audit_logs"]
    assert any(l["action"] == "status_change" and l["before"]["status"] == "Draft" and l["after"]["status"] == "Paused" for l in logs)


def test_expense_approval_is_audited(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    expense = client.post("/api/expenses", data={"amount": "100", "category": "Food", "expense_date": "2026-01-10"}, content_type="multipart/form-data", headers=auth_header(token)).get_json()["expense"]
    client.patch(f"/api/expenses/{expense['id']}", json={"status": "Approved"}, headers=auth_header(token))

    resp = client.get(f"/api/audit-logs?resource_type=expense&resource_id={expense['id']}", headers=auth_header(token))
    logs = resp.get_json()["audit_logs"]
    assert any(l["action"] == "status_change" for l in logs)


def test_donation_status_change_is_audited(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    donation = client.post("/api/donations", json={"donor_name": "X", "donor_email": "xaudit@example.com", "amount": 100, "frequency": "one-time"}).get_json()["donation"]
    client.patch(f"/api/donations/{donation['id']}", json={"status": "Pending"}, headers=auth_header(token))

    resp = client.get(f"/api/audit-logs?resource_type=donation&resource_id={donation['id']}", headers=auth_header(token))
    logs = resp.get_json()["audit_logs"]
    assert any(l["action"] == "status_change" for l in logs)


def test_staff_cannot_access_audit_log(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.get("/api/audit-logs", headers=auth_header(token))
    assert resp.status_code == 403


def test_volunteer_cannot_access_audit_log(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.get("/api/audit-logs", headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_audit_log(client):
    assert client.get("/api/audit-logs").status_code == 401
