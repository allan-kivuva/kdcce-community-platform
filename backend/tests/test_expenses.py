import io

VALID = {"amount": "5000", "category": "Food", "expense_date": "2026-01-15"}
PDF_BYTES = b"%PDF-1.4" + b"\x00" * 100
NOT_A_FILE = b"this is not a real file" + b"\x00" * 100


def test_admin_can_record_expense(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/expenses", data=VALID, content_type="multipart/form-data", headers=auth_header(token))
    assert resp.status_code == 201
    body = resp.get_json()["expense"]
    assert body["amount"] == 5000.0
    assert body["status"] == "Recorded"


def test_staff_can_record_expense(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/expenses", data=VALID, content_type="multipart/form-data", headers=auth_header(token))
    assert resp.status_code == 201


def test_volunteer_cannot_record_expense(client, make_user, auth_header):
    _, token, _ = make_user()
    resp = client.post("/api/expenses", data=VALID, content_type="multipart/form-data", headers=auth_header(token))
    assert resp.status_code == 403


def test_amount_must_be_positive(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/expenses", data={**VALID, "amount": "0"}, content_type="multipart/form-data", headers=auth_header(token))
    assert resp.status_code == 400


def test_invalid_category_rejected(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/expenses", data={**VALID, "category": "Not A Category"}, content_type="multipart/form-data", headers=auth_header(token))
    assert resp.status_code == 400


def test_expense_can_link_to_a_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json={"name": "Feeding", "status": "Active"}, headers=auth_header(token)).get_json()["program"]
    resp = client.post("/api/expenses", data={**VALID, "program_id": str(program["id"])}, content_type="multipart/form-data", headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["expense"]["program_name"] == "Feeding"


def test_expense_rejects_unknown_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/expenses", data={**VALID, "program_id": "999999"}, content_type="multipart/form-data", headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Receipt upload ----------

def test_expense_with_receipt_upload(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post(
        "/api/expenses", data={**VALID, "file": (io.BytesIO(PDF_BYTES), "receipt.pdf")},
        content_type="multipart/form-data", headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.get_json()["expense"]["document_id"] is not None


def test_expense_receipt_rejects_disguised_file(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post(
        "/api/expenses", data={**VALID, "file": (io.BytesIO(NOT_A_FILE), "fake.pdf")},
        content_type="multipart/form-data", headers=auth_header(token),
    )
    assert resp.status_code == 400


def test_admin_can_download_receipt(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = client.post(
        "/api/expenses", data={**VALID, "file": (io.BytesIO(PDF_BYTES), "receipt.pdf")},
        content_type="multipart/form-data", headers=auth_header(token),
    ).get_json()["expense"]
    resp = client.get(f"/api/expenses/{created['id']}/receipt", headers=auth_header(token))
    assert resp.status_code == 200


def test_volunteer_cannot_download_receipt(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post(
        "/api/expenses", data={**VALID, "file": (io.BytesIO(PDF_BYTES), "receipt.pdf")},
        content_type="multipart/form-data", headers=auth_header(admin_token),
    ).get_json()["expense"]
    _, vol_token, _ = make_user()
    resp = client.get(f"/api/expenses/{created['id']}/receipt", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_download_receipt(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post(
        "/api/expenses", data={**VALID, "file": (io.BytesIO(PDF_BYTES), "receipt.pdf")},
        content_type="multipart/form-data", headers=auth_header(admin_token),
    ).get_json()["expense"]
    resp = client.get(f"/api/expenses/{created['id']}/receipt")
    assert resp.status_code == 401


# ---------- Approval workflow ----------

def test_staff_can_edit_descriptive_fields(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    created = client.post("/api/expenses", data=VALID, content_type="multipart/form-data", headers=auth_header(token)).get_json()["expense"]
    resp = client.patch(f"/api/expenses/{created['id']}", json={"vendor_name": "ACME Foods"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["expense"]["vendor_name"] == "ACME Foods"


def test_staff_cannot_approve_expense(client, make_staff_user, auth_header):
    _, staff_token = make_staff_user("staff")
    created = client.post("/api/expenses", data=VALID, content_type="multipart/form-data", headers=auth_header(staff_token)).get_json()["expense"]
    resp = client.patch(f"/api/expenses/{created['id']}", json={"status": "Approved"}, headers=auth_header(staff_token))
    assert resp.status_code == 403


def test_admin_can_approve_expense(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/expenses", data=VALID, content_type="multipart/form-data", headers=auth_header(admin_token)).get_json()["expense"]
    resp = client.patch(f"/api/expenses/{created['id']}", json={"status": "Approved"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    body = resp.get_json()["expense"]
    assert body["status"] == "Approved"
    assert body["approved_by"] is not None
    assert body["approved_at"] is not None


def test_admin_can_void_expense(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/expenses", data=VALID, content_type="multipart/form-data", headers=auth_header(admin_token)).get_json()["expense"]
    resp = client.patch(f"/api/expenses/{created['id']}", json={"status": "Voided"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["expense"]["status"] == "Voided"


def test_volunteer_cannot_edit_expense(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/expenses", data=VALID, content_type="multipart/form-data", headers=auth_header(admin_token)).get_json()["expense"]
    _, vol_token, _ = make_user()
    resp = client.patch(f"/api/expenses/{created['id']}", json={"vendor_name": "Hacked"}, headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_expenses(client):
    assert client.get("/api/expenses").status_code == 401
