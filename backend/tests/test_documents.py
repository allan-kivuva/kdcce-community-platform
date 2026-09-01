import io
from datetime import date, timedelta

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PDF_BYTES = b"%PDF-1.4" + b"\x00" * 100
NOT_A_DOCUMENT = b"this is definitely not a document file" + b"\x00" * 100
OVERSIZED_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * (5 * 1024 * 1024 + 1)
OVERSIZED_PDF = b"%PDF-1.4" + b"\x00" * (10 * 1024 * 1024 + 1)


def _verified_volunteer(client, make_user, auth_header, admin_token, email="doc-vol@example.com"):
    user, access_token, _ = make_user(email=email, name="Document Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token, vid


def _upload(client, token, auth_header, data=JPEG_BYTES, filename="id.jpg", document_type="Identification", title="My ID", **extra):
    form = {"document_type": document_type, "title": title, **extra}
    if data is not None:
        form["file"] = (io.BytesIO(data), filename)
    return client.post("/api/volunteers/me/documents", data=form, content_type="multipart/form-data", headers=auth_header(token))


# ---------- Upload / validation ----------

def test_volunteer_can_upload_a_jpeg_document(client, make_user, auth_header):
    _, token, _ = make_user(email="upload-jpg@example.com")
    resp = _upload(client, token, auth_header, JPEG_BYTES, "id.jpg")
    assert resp.status_code == 201
    body = resp.get_json()["document"]
    assert body["mime_type"] == "image/jpeg"
    assert body["status"] == "Pending"


def test_volunteer_can_upload_a_pdf_document(client, make_user, auth_header):
    _, token, _ = make_user(email="upload-pdf@example.com")
    resp = _upload(client, token, auth_header, PDF_BYTES, "agreement.pdf", document_type="Volunteer Agreement", title="Signed Agreement")
    assert resp.status_code == 201
    assert resp.get_json()["document"]["mime_type"] == "application/pdf"


def test_upload_rejects_a_disguised_non_document_file(client, make_user, auth_header):
    """Magic-byte sniffing, not filename/extension trust — a .jpg
    extension on non-image bytes must still be rejected."""
    _, token, _ = make_user(email="upload-fake@example.com")
    resp = _upload(client, token, auth_header, NOT_A_DOCUMENT, "id.jpg")
    assert resp.status_code == 400
    assert "file" in resp.get_json()["details"]


def test_upload_rejects_oversized_image(client, make_user, auth_header):
    _, token, _ = make_user(email="upload-bigimg@example.com")
    resp = _upload(client, token, auth_header, OVERSIZED_JPEG, "big.jpg")
    assert resp.status_code == 400


def test_upload_rejects_oversized_pdf(client, make_user, auth_header):
    _, token, _ = make_user(email="upload-bigpdf@example.com")
    resp = _upload(client, token, auth_header, OVERSIZED_PDF, "big.pdf", document_type="Certificate", title="Big cert")
    assert resp.status_code == 400


def test_upload_requires_a_file(client, make_user, auth_header):
    _, token, _ = make_user(email="upload-nofile@example.com")
    resp = _upload(client, token, auth_header, data=None)
    assert resp.status_code == 400


def test_upload_rejects_invalid_document_type(client, make_user, auth_header):
    _, token, _ = make_user(email="upload-badtype@example.com")
    resp = _upload(client, token, auth_header, document_type="Not A Real Type")
    assert resp.status_code == 400


def test_upload_rejects_expiry_before_issue_date(client, make_user, auth_header):
    _, token, _ = make_user(email="upload-baddate@example.com")
    resp = _upload(client, token, auth_header, issue_date="2026-06-01", expiry_date="2026-01-01")
    assert resp.status_code == 400


def test_unauthenticated_cannot_upload(client):
    resp = client.post("/api/volunteers/me/documents", data={"document_type": "Identification", "title": "x", "file": (io.BytesIO(JPEG_BYTES), "x.jpg")}, content_type="multipart/form-data")
    assert resp.status_code == 401


# ---------- Ownership / access ----------

def test_volunteer_sees_own_documents(client, make_user, auth_header):
    _, token, _ = make_user(email="ownlist@example.com")
    _upload(client, token, auth_header)
    documents = client.get("/api/volunteers/me/documents", headers=auth_header(token)).get_json()["documents"]
    assert len(documents) == 1


def test_volunteer_cannot_see_another_volunteers_documents(client, make_user, auth_header):
    _, token_a, _ = make_user(email="docs-a@example.com")
    _, token_b, _ = make_user(email="docs-b@example.com")
    _upload(client, token_a, auth_header)
    documents_b = client.get("/api/volunteers/me/documents", headers=auth_header(token_b)).get_json()["documents"]
    assert documents_b == []


def test_volunteer_cannot_download_another_volunteers_document_file(client, make_user, auth_header):
    _, token_a, _ = make_user(email="docsfile-a@example.com")
    _, token_b, _ = make_user(email="docsfile-b@example.com")
    doc_id = _upload(client, token_a, auth_header).get_json()["document"]["id"]
    resp = client.get(f"/api/documents/{doc_id}/file", headers=auth_header(token_b))
    assert resp.status_code == 403


def test_owner_can_download_their_own_document_file(client, make_user, auth_header):
    _, token, _ = make_user(email="ownfile@example.com")
    doc_id = _upload(client, token, auth_header, JPEG_BYTES).get_json()["document"]["id"]
    resp = client.get(f"/api/documents/{doc_id}/file", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.data.startswith(b"\xff\xd8\xff")


def test_admin_can_view_a_volunteers_documents(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    user, token, vid = _verified_volunteer(client, make_user, auth_header, admin_token)
    _upload(client, token, auth_header)

    resp = client.get(f"/api/volunteers/{vid}/documents", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert len(resp.get_json()["documents"]) == 1


def test_volunteer_cannot_list_another_volunteers_documents_via_admin_route(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    user, token, vid = _verified_volunteer(client, make_user, auth_header, admin_token)
    resp = client.get(f"/api/volunteers/{vid}/documents", headers=auth_header(token))
    assert resp.status_code == 403


# ---------- Admin review ----------

def test_admin_can_verify_a_document_and_it_notifies(client, make_user, auth_header, make_staff_user):
    _, token, _ = make_user(email="verifyme@example.com")
    _, admin_token = make_staff_user("admin")
    doc_id = _upload(client, token, auth_header).get_json()["document"]["id"]

    resp = client.patch(f"/api/documents/{doc_id}/status", json={"status": "Verified"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["document"]["status"] == "Verified"

    notifications = client.get("/api/notifications", headers=auth_header(token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Document Verified" for n in notifications)


def test_admin_can_reject_a_document_with_reason_and_it_notifies(client, make_user, auth_header, make_staff_user):
    _, token, _ = make_user(email="rejectme@example.com")
    _, admin_token = make_staff_user("admin")
    doc_id = _upload(client, token, auth_header).get_json()["document"]["id"]

    resp = client.patch(f"/api/documents/{doc_id}/status", json={"status": "Rejected", "rejection_reason": "Blurry photo"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["document"]["rejection_reason"] == "Blurry photo"

    notifications = client.get("/api/notifications", headers=auth_header(token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Document Rejected" for n in notifications)


def test_verifying_a_document_is_audited(client, make_user, auth_header, make_staff_user):
    _, token, _ = make_user(email="verifyaudit@example.com")
    _, admin_token = make_staff_user("admin")
    doc_id = _upload(client, token, auth_header).get_json()["document"]["id"]

    resp = client.patch(f"/api/documents/{doc_id}/status", json={"status": "Verified"}, headers=auth_header(admin_token))
    assert resp.status_code == 200

    logs_resp = client.get(
        f"/api/audit-logs?resource_type=document&resource_id={doc_id}", headers=auth_header(admin_token)
    )
    logs = logs_resp.get_json()["audit_logs"]
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "verify"
    assert log["resource_id"] == doc_id
    assert log["before"]["status"] == "Pending"
    assert log["after"]["status"] == "Verified"
    for snapshot in (log["before"], log["after"]):
        for key in snapshot:
            assert "password" not in key.lower()
            assert "token" not in key.lower()


def test_rejecting_without_a_reason_is_rejected(client, make_user, auth_header, make_staff_user):
    _, token, _ = make_user(email="noreasonreject@example.com")
    _, admin_token = make_staff_user("admin")
    doc_id = _upload(client, token, auth_header).get_json()["document"]["id"]
    resp = client.patch(f"/api/documents/{doc_id}/status", json={"status": "Rejected"}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_volunteer_cannot_verify_their_own_document(client, make_user, auth_header):
    _, token, _ = make_user(email="selfverify@example.com")
    doc_id = _upload(client, token, auth_header).get_json()["document"]["id"]
    resp = client.patch(f"/api/documents/{doc_id}/status", json={"status": "Verified"}, headers=auth_header(token))
    assert resp.status_code == 403


# ---------- Expiry ----------

def test_expiry_state_valid_when_far_in_the_future(client, make_user, auth_header):
    _, token, _ = make_user(email="expiryvalid@example.com")
    far_future = (date.today() + timedelta(days=200)).isoformat()
    doc_id = _upload(client, token, auth_header, expiry_date=far_future).get_json()["document"]["id"]
    documents = client.get("/api/volunteers/me/documents", headers=auth_header(token)).get_json()["documents"]
    assert documents[0]["expiry_state"] == "valid"


def test_expiry_state_expiring_soon_within_30_days(client, make_user, auth_header):
    _, token, _ = make_user(email="expirysoon@example.com")
    soon = (date.today() + timedelta(days=10)).isoformat()
    _upload(client, token, auth_header, expiry_date=soon)
    documents = client.get("/api/volunteers/me/documents", headers=auth_header(token)).get_json()["documents"]
    assert documents[0]["expiry_state"] == "expiring_soon"


def test_expiry_state_expired_when_in_the_past(client, make_user, auth_header):
    _, token, _ = make_user(email="expirypast@example.com")
    past = (date.today() - timedelta(days=5)).isoformat()
    _upload(client, token, auth_header, expiry_date=past)
    documents = client.get("/api/volunteers/me/documents", headers=auth_header(token)).get_json()["documents"]
    assert documents[0]["expiry_state"] == "expired"


def test_expiry_state_null_when_no_expiry_date(client, make_user, auth_header):
    _, token, _ = make_user(email="noexpiry@example.com")
    _upload(client, token, auth_header)
    documents = client.get("/api/volunteers/me/documents", headers=auth_header(token)).get_json()["documents"]
    assert documents[0]["expiry_state"] is None


# ---------- Delete ----------

def test_owner_can_delete_own_pending_document(client, make_user, auth_header):
    _, token, _ = make_user(email="deletepending@example.com")
    doc_id = _upload(client, token, auth_header).get_json()["document"]["id"]
    resp = client.delete(f"/api/documents/{doc_id}", headers=auth_header(token))
    assert resp.status_code == 204
    assert client.get("/api/volunteers/me/documents", headers=auth_header(token)).get_json()["documents"] == []


def test_owner_cannot_delete_after_it_has_been_reviewed(client, make_user, auth_header, make_staff_user):
    _, token, _ = make_user(email="deleteafterreview@example.com")
    _, admin_token = make_staff_user("admin")
    doc_id = _upload(client, token, auth_header).get_json()["document"]["id"]
    client.patch(f"/api/documents/{doc_id}/status", json={"status": "Verified"}, headers=auth_header(admin_token))

    resp = client.delete(f"/api/documents/{doc_id}", headers=auth_header(token))
    assert resp.status_code == 403


def test_admin_can_delete_any_document(client, make_user, auth_header, make_staff_user):
    _, token, _ = make_user(email="admindelete@example.com")
    _, admin_token = make_staff_user("admin")
    doc_id = _upload(client, token, auth_header).get_json()["document"]["id"]
    resp = client.delete(f"/api/documents/{doc_id}", headers=auth_header(admin_token))
    assert resp.status_code == 204
