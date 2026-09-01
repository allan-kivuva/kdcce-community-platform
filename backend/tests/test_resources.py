import io

PDF_BYTES = b"%PDF-1.4" + b"\x00" * 100
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100
NOT_A_FILE = b"this is not a real file" + b"\x00" * 100


def _verified_volunteer(client, make_user, auth_header, admin_token, email="res-vol@example.com"):
    user, access_token, _ = make_user(email=email, name="Resource Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _upload(client, token, auth_header, data=PDF_BYTES, filename="guide.pdf", **extra):
    form = {"title": "Volunteer Handbook", "category": "Volunteer Instructions", "visibility": "Volunteers", **extra}
    if data is not None:
        form["file"] = (io.BytesIO(data), filename)
    return client.post("/api/resources", data=form, content_type="multipart/form-data", headers=auth_header(token))


# ---------- Upload / authorization ----------

def test_admin_can_upload_a_general_resource(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = _upload(client, token, auth_header)
    assert resp.status_code == 201
    body = resp.get_json()["resource"]
    assert body["title"] == "Volunteer Handbook"
    assert body["status"] == "Verified"  # auto-verified, no review workflow for admin-uploaded resources
    assert body["owner_type"] == "general"


def test_staff_can_upload_a_resource(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = _upload(client, token, auth_header)
    assert resp.status_code == 201


def test_volunteer_cannot_upload_a_resource(client, make_user, auth_header):
    _, token, _ = make_user(email="noupload@example.com")
    resp = _upload(client, token, auth_header)
    assert resp.status_code == 403


def test_upload_rejects_a_disguised_file(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = _upload(client, token, auth_header, data=NOT_A_FILE, filename="fake.pdf")
    assert resp.status_code == 400


def test_upload_rejects_invalid_category(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = _upload(client, token, auth_header, category="Not A Real Category")
    assert resp.status_code == 400


def test_unauthenticated_cannot_list_resources(client):
    assert client.get("/api/resources").status_code == 401


# ---------- Program/activity linking ----------

def test_resource_can_be_tied_to_a_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json={"name": "Feeding Program"}, headers=auth_header(token)).get_json()["program"]
    resp = _upload(client, token, auth_header, program_id=str(program["id"]))
    assert resp.status_code == 201
    assert resp.get_json()["resource"]["owner_type"] == "program"
    assert resp.get_json()["resource"]["owner_id"] == program["id"]


def test_resource_can_be_tied_to_an_activity(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    activity = client.post("/api/activities", json={"title": "Fair", "activity_type": "Community Event", "scheduled_at": "2027-05-01T09:00:00+00:00"}, headers=auth_header(token)).get_json()["activity"]
    resp = _upload(client, token, auth_header, activity_id=str(activity["id"]))
    assert resp.status_code == 201
    assert resp.get_json()["resource"]["owner_type"] == "activity"
    assert resp.get_json()["resource"]["owner_id"] == activity["id"]


def test_resource_rejects_unknown_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = _upload(client, token, auth_header, program_id="999999")
    assert resp.status_code == 400


def test_resources_filterable_by_program(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    program = client.post("/api/programs", json={"name": "Health Program"}, headers=auth_header(token)).get_json()["program"]
    _upload(client, token, auth_header, program_id=str(program["id"]), title="In program")
    _upload(client, token, auth_header, title="Not in program")

    resp = client.get(f"/api/resources?program_id={program['id']}", headers=auth_header(token))
    titles = [r["title"] for r in resp.get_json()["resources"]]
    assert titles == ["In program"]


# ---------- Visibility ----------

def test_admin_visibility_hidden_from_volunteers(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _upload(client, admin_token, auth_header, visibility="Admin", title="Staff only doc")
    _, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.get("/api/resources", headers=auth_header(vol_token))
    titles = [r["title"] for r in resp.get_json()["resources"]]
    assert "Staff only doc" not in titles


def test_volunteers_visibility_shown_to_volunteers(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _upload(client, admin_token, auth_header, visibility="Volunteers", title="For everyone")
    _, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.get("/api/resources", headers=auth_header(vol_token))
    titles = [r["title"] for r in resp.get_json()["resources"]]
    assert "For everyone" in titles


def test_admin_sees_both_visibility_levels(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    _upload(client, token, auth_header, visibility="Admin", title="Admin doc")
    _upload(client, token, auth_header, visibility="Volunteers", title="Vol doc")

    resp = client.get("/api/resources", headers=auth_header(token))
    titles = [r["title"] for r in resp.get_json()["resources"]]
    assert "Admin doc" in titles
    assert "Vol doc" in titles


def test_volunteer_documents_never_appear_in_resource_listing(client, make_user, auth_header):
    """A volunteer's own uploaded ID/certificate (visibility=None) must
    never leak into the resource library listing."""
    _, token, _ = make_user(email="ownerofdoc@example.com")
    client.post(
        "/api/volunteers/me/documents",
        data={"document_type": "Identification", "title": "My Private ID", "file": (io.BytesIO(JPEG_BYTES), "id.jpg")},
        content_type="multipart/form-data", headers=auth_header(token),
    )
    resp = client.get("/api/resources", headers=auth_header(token))
    titles = [r["title"] for r in resp.get_json()["resources"]]
    assert "My Private ID" not in titles


# ---------- Download / delete authorization ----------

def test_volunteer_can_download_a_volunteer_visible_resource(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = _upload(client, admin_token, auth_header, visibility="Volunteers").get_json()["resource"]
    _, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.get(f"/api/resources/{created['id']}/file", headers=auth_header(vol_token))
    assert resp.status_code == 200


def test_volunteer_cannot_download_an_admin_only_resource(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = _upload(client, admin_token, auth_header, visibility="Admin").get_json()["resource"]
    _, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)

    resp = client.get(f"/api/resources/{created['id']}/file", headers=auth_header(vol_token))
    assert resp.status_code == 404


def test_volunteer_cannot_delete_a_resource(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = _upload(client, admin_token, auth_header).get_json()["resource"]
    _, vol_token, _ = make_user(email="nodelete@example.com")

    resp = client.delete(f"/api/resources/{created['id']}", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_admin_can_delete_a_resource(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    created = _upload(client, token, auth_header).get_json()["resource"]
    resp = client.delete(f"/api/resources/{created['id']}", headers=auth_header(token))
    assert resp.status_code == 204
    assert client.get("/api/resources", headers=auth_header(token)).get_json()["resources"] == []


def test_delete_resource_does_not_touch_a_volunteers_own_document(client, make_user, make_staff_user, auth_header):
    """The resources DELETE endpoint must refuse to delete a volunteer's
    own document (visibility=None) even if an admin guesses its id —
    that deletion path belongs to documents/routes.py only."""
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="protecteddoc@example.com")
    doc = client.post(
        "/api/volunteers/me/documents",
        data={"document_type": "Identification", "title": "Protected", "file": (io.BytesIO(JPEG_BYTES), "id.jpg")},
        content_type="multipart/form-data", headers=auth_header(vol_token),
    ).get_json()["document"]

    resp = client.delete(f"/api/resources/{doc['id']}", headers=auth_header(admin_token))
    assert resp.status_code == 404
