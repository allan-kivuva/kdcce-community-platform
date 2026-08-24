import io

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 100
NOT_AN_IMAGE = b"this is definitely not an image file" + b"\x00" * 100
OVERSIZED_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * (5 * 1024 * 1024 + 1)

VALID_REASON = {"reason": "Unable to attend the centre due to mobility issues"}
VALID_ASSISTANCE = {"request_type": "Companionship", "description": "Would like a weekly visitor"}


def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _make_visit(client, admin_token, auth_header, assignee_id, member=None):
    member = member or _register_member(client, admin_token, auth_header)
    resp = client.post(
        "/api/home-visits",
        json={"elderly_member_id": member["id"], "assigned_to_id": assignee_id, **VALID_REASON},
        headers=auth_header(admin_token),
    )
    return resp.get_json()["visit"]


def _upload(client, url, token, auth_header, data=JPEG_BYTES, filename="photo.jpg"):
    return client.post(
        url,
        data={"photo": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
        headers=auth_header(token),
    )


# ---------- Photo upload: format/size validation ----------

def test_upload_valid_jpeg(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header, JPEG_BYTES, "a.jpg")
    assert resp.status_code == 201
    body = resp.get_json()["attachment"]
    assert body["mime_type"] == "image/jpeg"
    assert body["file_size"] == len(JPEG_BYTES)


def test_upload_valid_png(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header, PNG_BYTES, "a.png")
    assert resp.status_code == 201
    assert resp.get_json()["attachment"]["mime_type"] == "image/png"


def test_upload_valid_webp(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header, WEBP_BYTES, "a.webp")
    assert resp.status_code == 201
    assert resp.get_json()["attachment"]["mime_type"] == "image/webp"


def test_completing_without_a_photo_is_fine(client, make_user, make_staff_user, auth_header):
    """The photo is optional — completing the assignment via the existing
    PATCH endpoint never requires one, and no attachment row is created
    unless the volunteer explicitly uploads one."""
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed", "observations": "All well."}, headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["visit"]["status"] == "Completed"

    photo_resp = client.get(f"/api/home-visits/{visit['id']}/photo", headers=auth_header(vol_token))
    assert photo_resp.status_code == 404


def test_upload_rejects_non_image_file(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header, NOT_AN_IMAGE, "a.txt")
    assert resp.status_code == 400
    assert "photo" in resp.get_json()["details"]


def test_upload_rejects_oversized_file(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header, OVERSIZED_JPEG, "big.jpg")
    assert resp.status_code in (400, 413)  # 413 if Werkzeug's MAX_CONTENT_LENGTH backstop fires first


def test_upload_rejects_missing_file(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.post(f"/api/home-visits/{visit['id']}/photo", data={}, content_type="multipart/form-data", headers=auth_header(vol_token))
    assert resp.status_code == 400


def test_reupload_replaces_the_existing_photo(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header, JPEG_BYTES, "first.jpg")
    resp = _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header, PNG_BYTES, "second.png")
    assert resp.status_code == 201

    fetched = client.get(f"/api/home-visits/{visit['id']}/photo", headers=auth_header(vol_token))
    assert fetched.status_code == 200
    assert fetched.content_type == "image/png"


def test_photo_content_type_is_the_server_verified_one(client, make_user, make_staff_user, auth_header):
    """Uploading a JPEG's real bytes with a misleading .png filename must
    still be identified and served as image/jpeg — the server never
    trusts the client-provided filename/extension."""
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header, JPEG_BYTES, "lying.png")
    fetched = client.get(f"/api/home-visits/{visit['id']}/photo", headers=auth_header(vol_token))
    assert fetched.content_type == "image/jpeg"


# ---------- Photo privacy / authorization ----------

def test_unauthenticated_cannot_access_photo(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])
    _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header)

    resp = client.get(f"/api/home-visits/{visit['id']}/photo")
    assert resp.status_code == 401


def test_other_volunteer_cannot_view_photo(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-a@example.com")
    _, vol_b_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-b@example.com")
    visit = _make_visit(client, admin_token, auth_header, vol_a["id"])
    _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_a_token, auth_header)

    resp = client.get(f"/api/home-visits/{visit['id']}/photo", headers=auth_header(vol_b_token))
    assert resp.status_code == 403


def test_other_volunteer_cannot_upload_to_someone_elses_visit(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-a2@example.com")
    _, vol_b_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-b2@example.com")
    visit = _make_visit(client, admin_token, auth_header, vol_a["id"])

    resp = _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_b_token, auth_header)
    assert resp.status_code == 403


def test_admin_can_view_any_photo(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])
    _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header)

    resp = client.get(f"/api/home-visits/{visit['id']}/photo", headers=auth_header(admin_token))
    assert resp.status_code == 200


def test_rejected_volunteer_loses_photo_access(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="soon-rejected@example.com")
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])
    _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header)

    vid = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    volunteer_id = next(v for v in vid if v["email"] == "soon-rejected@example.com")["id"]
    client.patch(f"/api/volunteers/{volunteer_id}", json={"status": "Rejected"}, headers=auth_header(admin_token))

    resp = client.get(f"/api/home-visits/{visit['id']}/photo", headers=auth_header(vol_token))
    assert resp.status_code == 403


def test_photo_never_reachable_via_a_public_static_path(client, make_user, make_staff_user, auth_header):
    """There is no static-file route serving the upload directory at
    all — confirms the file is only ever reachable through the
    authenticated endpoint, never a guessable public URL."""
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])
    upload_resp = _upload(client, f"/api/home-visits/{visit['id']}/photo", vol_token, auth_header)
    storage_key_guess_paths = [
        "/static/uploads/assignment_photos/",
        "/uploads/assignment_photos/",
        "/instance/uploads/assignment_photos/",
    ]
    for path in storage_key_guess_paths:
        assert client.get(path).status_code == 404


# ---------- Assignment security (privileged fields, cross-assignment) ----------

def test_volunteer_can_access_own_assignment_messages(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.get(f"/api/home-visits/{visit['id']}/messages", headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert resp.get_json()["messages"] == []


def test_volunteer_cannot_access_another_volunteers_assignment_messages(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, _ = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-a3@example.com")
    _, vol_b_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-b3@example.com")
    visit = _make_visit(client, admin_token, auth_header, vol_a["id"])

    resp = client.get(f"/api/home-visits/{visit['id']}/messages", headers=auth_header(vol_b_token))
    assert resp.status_code == 403


def test_volunteer_cannot_modify_privileged_fields_via_existing_patch(client, make_user, make_staff_user, auth_header):
    """Regression guard: this feature must not have loosened the existing
    outcome-only PATCH restriction for a volunteer's own visit."""
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"priority": "Urgent"}, headers=auth_header(vol_token))
    assert resp.status_code == 400
    resp = client.patch(f"/api/home-visits/{visit['id']}", json={"assigned_to_id": vol_user["id"]}, headers=auth_header(vol_token))
    assert resp.status_code == 400


# ---------- Messaging ----------

def test_volunteer_can_send_message_and_admin_can_reply(client, make_user, make_staff_user, auth_header):
    admin_user, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.post(f"/api/home-visits/{visit['id']}/messages", json={"body": "Visit completed. She'd like help with her next clinic appointment."}, headers=auth_header(vol_token))
    assert resp.status_code == 201
    assert resp.get_json()["message"]["sender_name"] == vol_user["name"]

    reply = client.post(f"/api/home-visits/{visit['id']}/messages", json={"body": "Thanks, we'll arrange the follow-up."}, headers=auth_header(admin_token))
    assert reply.status_code == 201

    thread = client.get(f"/api/home-visits/{visit['id']}/messages", headers=auth_header(admin_token)).get_json()["messages"]
    assert len(thread) == 2
    assert thread[0]["body"].startswith("Visit completed")
    assert thread[1]["body"].startswith("Thanks")


def test_messages_are_scoped_to_the_correct_assignment(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    member = _register_member(client, admin_token, auth_header)
    visit_1 = _make_visit(client, admin_token, auth_header, vol_user["id"], member=member)
    visit_2 = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol_user["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]

    client.post(f"/api/home-visits/{visit_1['id']}/messages", json={"body": "Message on visit 1"}, headers=auth_header(vol_token))
    client.post(f"/api/home-visits/{visit_2['id']}/messages", json={"body": "Message on visit 2"}, headers=auth_header(vol_token))

    thread_1 = client.get(f"/api/home-visits/{visit_1['id']}/messages", headers=auth_header(vol_token)).get_json()["messages"]
    assert len(thread_1) == 1
    assert thread_1[0]["body"] == "Message on visit 1"


def test_volunteer_cannot_read_another_volunteers_conversation(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-a4@example.com")
    _, vol_b_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-b4@example.com")
    visit = _make_visit(client, admin_token, auth_header, vol_a["id"])
    client.post(f"/api/home-visits/{visit['id']}/messages", json={"body": "private note"}, headers=auth_header(vol_a_token))

    resp = client.post(f"/api/home-visits/{visit['id']}/messages", json={"body": "trying to read this thread"}, headers=auth_header(vol_b_token))
    assert resp.status_code == 403


def test_sending_a_message_notifies_the_other_party(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    client.post(f"/api/home-visits/{visit['id']}/messages", json={"body": "Update on the visit"}, headers=auth_header(vol_token))
    notifications = client.get("/api/notifications?notification_type=Assignment%20Message", headers=auth_header(admin_token)).get_json()["notifications"]
    assert len(notifications) == 1
    assert "Update on the visit" in notifications[0]["message"]


def test_empty_message_body_rejected(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = _make_visit(client, admin_token, auth_header, vol_user["id"])

    resp = client.post(f"/api/home-visits/{visit['id']}/messages", json={"body": ""}, headers=auth_header(vol_token))
    assert resp.status_code == 400


# ---------- Assistance requests: same mechanism, spot-checked ----------

def _make_assistance_request(client, admin_token, auth_header, assignee_id):
    member = _register_member(client, admin_token, auth_header)
    resp = client.post(
        "/api/assistance-requests",
        json={"elderly_member_id": member["id"], "assigned_to_id": assignee_id, **VALID_ASSISTANCE},
        headers=auth_header(admin_token),
    )
    return resp.get_json()["request"]


def test_assistance_request_photo_upload_and_privacy(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_a, vol_a_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-ar-a@example.com")
    _, vol_b_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="vol-ar-b@example.com")
    req = _make_assistance_request(client, admin_token, auth_header, vol_a["id"])

    resp = _upload(client, f"/api/assistance-requests/{req['id']}/photo", vol_a_token, auth_header)
    assert resp.status_code == 201

    assert client.get(f"/api/assistance-requests/{req['id']}/photo", headers=auth_header(vol_a_token)).status_code == 200
    assert client.get(f"/api/assistance-requests/{req['id']}/photo", headers=auth_header(vol_b_token)).status_code == 403
    assert client.get(f"/api/assistance-requests/{req['id']}/photo").status_code == 401


def test_assistance_request_messaging(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol_user, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    req = _make_assistance_request(client, admin_token, auth_header, vol_user["id"])

    resp = client.post(f"/api/assistance-requests/{req['id']}/messages", json={"body": "On my way"}, headers=auth_header(vol_token))
    assert resp.status_code == 201

    thread = client.get(f"/api/assistance-requests/{req['id']}/messages", headers=auth_header(admin_token)).get_json()["messages"]
    assert len(thread) == 1
