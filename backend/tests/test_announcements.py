from datetime import timedelta

from app.models import utcnow

VALID = {"title": "Office closed Friday", "body": "The centre will be closed for staff training.", "audience_type": "All"}


def _verified_volunteer(client, make_user, auth_header, admin_token, email="vera@example.com"):
    user, access_token, _ = make_user(email=email, name="Vera Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _iso(dt):
    return dt.isoformat()


# ---------- Create / permissions ----------

def test_admin_can_create_announcement(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/announcements", json=VALID, headers=auth_header(token))
    assert resp.status_code == 201
    assert resp.get_json()["announcement"]["priority"] == "Normal"


def test_staff_can_create_announcement(client, make_staff_user, auth_header):
    _, token = make_staff_user("staff")
    resp = client.post("/api/announcements", json=VALID, headers=auth_header(token))
    assert resp.status_code == 201


def test_volunteer_cannot_create_announcement(client, make_user, auth_header):
    _, token, _ = make_user(email="noannounce@example.com")
    resp = client.post("/api/announcements", json=VALID, headers=auth_header(token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_list_announcements(client):
    assert client.get("/api/announcements").status_code == 401


def test_selected_audience_requires_user_ids(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/announcements", json={**VALID, "audience_type": "Selected"}, headers=auth_header(token))
    assert resp.status_code == 400


# ---------- Active filtering / audience targeting ----------

def test_all_audience_visible_to_volunteer_and_staff(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    client.post("/api/announcements", json=VALID, headers=auth_header(admin_token))
    _, vol_token, _ = make_user(email="seesall@example.com")

    resp = client.get("/api/announcements", headers=auth_header(vol_token))
    assert resp.status_code == 200
    assert any(a["title"] == VALID["title"] for a in resp.get_json()["announcements"])


def test_volunteers_only_audience_hidden_from_staff(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    client.post("/api/announcements", json={**VALID, "title": "Vol-only", "audience_type": "Volunteers"}, headers=auth_header(admin_token))
    _, staff_token = make_staff_user("staff", email="staffviewer@example.com")

    resp = client.get("/api/announcements", headers=auth_header(staff_token))
    assert all(a["title"] != "Vol-only" for a in resp.get_json()["announcements"])


def test_verified_volunteers_audience_hides_from_unverified(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    client.post("/api/announcements", json={**VALID, "title": "Verified-only", "audience_type": "Verified Volunteers"}, headers=auth_header(admin_token))

    _, pending_token, _ = make_user(email="pendingannounce@example.com")
    resp = client.get("/api/announcements", headers=auth_header(pending_token))
    assert all(a["title"] != "Verified-only" for a in resp.get_json()["announcements"])

    _, verified_token = _verified_volunteer(client, make_user, auth_header, admin_token, email="verifiedannounce@example.com")
    resp = client.get("/api/announcements", headers=auth_header(verified_token))
    assert any(a["title"] == "Verified-only" for a in resp.get_json()["announcements"])


def test_selected_audience_only_visible_to_chosen_users(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    chosen, chosen_token, _ = make_user(email="chosen@example.com")
    _, other_token, _ = make_user(email="notchosen@example.com")

    client.post("/api/announcements", json={**VALID, "title": "Just for you", "audience_type": "Selected", "selected_user_ids": [chosen["id"]]}, headers=auth_header(admin_token))

    resp = client.get("/api/announcements", headers=auth_header(chosen_token))
    assert any(a["title"] == "Just for you" for a in resp.get_json()["announcements"])

    resp = client.get("/api/announcements", headers=auth_header(other_token))
    assert all(a["title"] != "Just for you" for a in resp.get_json()["announcements"])


def test_expired_announcement_is_not_shown(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    past = _iso(utcnow() - timedelta(days=2))
    client.post("/api/announcements", json={**VALID, "title": "Old news", "expires_at": past}, headers=auth_header(admin_token))

    _, vol_token, _ = make_user(email="noexpired@example.com")
    resp = client.get("/api/announcements", headers=auth_header(vol_token))
    assert all(a["title"] != "Old news" for a in resp.get_json()["announcements"])


def test_scheduled_future_announcement_is_not_shown_yet(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    future = _iso(utcnow() + timedelta(days=2))
    client.post("/api/announcements", json={**VALID, "title": "Not yet", "publish_at": future}, headers=auth_header(admin_token))

    _, vol_token, _ = make_user(email="noscheduled@example.com")
    resp = client.get("/api/announcements", headers=auth_header(vol_token))
    assert all(a["title"] != "Not yet" for a in resp.get_json()["announcements"])


def test_inactive_announcement_is_not_shown(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/announcements", json={**VALID, "title": "Deactivated"}, headers=auth_header(admin_token)).get_json()["announcement"]
    client.patch(f"/api/announcements/{created['id']}", json={"active": False}, headers=auth_header(admin_token))

    _, vol_token, _ = make_user(email="noinactive@example.com")
    resp = client.get("/api/announcements", headers=auth_header(vol_token))
    assert all(a["title"] != "Deactivated" for a in resp.get_json()["announcements"])


def test_admin_all_view_includes_scheduled_and_expired(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    future = _iso(utcnow() + timedelta(days=2))
    client.post("/api/announcements", json={**VALID, "title": "Future one", "publish_at": future}, headers=auth_header(admin_token))

    resp = client.get("/api/announcements?all=true", headers=auth_header(admin_token))
    assert any(a["title"] == "Future one" for a in resp.get_json()["announcements"])


def test_volunteer_cannot_use_all_view(client, make_user, auth_header):
    _, vol_token, _ = make_user(email="noallview@example.com")
    resp = client.get("/api/announcements?all=true", headers=auth_header(vol_token))
    # Falls back to the scoped view rather than erroring — a volunteer
    # simply never sees the management listing regardless of the flag.
    assert resp.status_code == 200
    assert resp.get_json()["announcements"] == []


# ---------- Edit permissions ----------

def test_admin_can_edit_announcement(client, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/announcements", json=VALID, headers=auth_header(admin_token)).get_json()["announcement"]

    resp = client.patch(f"/api/announcements/{created['id']}", json={"title": "Updated title", "priority": "Urgent"}, headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()["announcement"]["title"] == "Updated title"
    assert resp.get_json()["announcement"]["priority"] == "Urgent"


def test_volunteer_cannot_edit_announcement(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    created = client.post("/api/announcements", json=VALID, headers=auth_header(admin_token)).get_json()["announcement"]
    _, vol_token, _ = make_user(email="noedit@example.com")

    resp = client.patch(f"/api/announcements/{created['id']}", json={"title": "Hacked"}, headers=auth_header(vol_token))
    assert resp.status_code == 403


# ---------- Notifications ----------

def test_creating_a_live_announcement_notifies_the_audience(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="notifyannounce@example.com")

    client.post("/api/announcements", json={**VALID, "title": "Live notice"}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Announcement" and "Live notice" in n["title"] for n in notifications)


def test_urgent_announcement_uses_urgent_notification_type(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="urgentnotify@example.com")

    client.post("/api/announcements", json={**VALID, "title": "Urgent notice", "priority": "Urgent"}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Urgent Announcement" for n in notifications)


def test_scheduled_announcement_does_not_notify_yet(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    _, vol_token, _ = make_user(email="noearlynotify@example.com")
    future = _iso(utcnow() + timedelta(days=2))

    client.post("/api/announcements", json={**VALID, "title": "Future notice", "publish_at": future}, headers=auth_header(admin_token))

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert all("Future notice" not in n["title"] for n in notifications)
