from datetime import timedelta

from app.extensions import db
from app.models import Achievement, HomeVisit, utcnow

VALID_REASON = {"reason": "Unable to attend the centre due to mobility issues"}


def _register_member(client, token, auth_header, name="Mary Achieng"):
    resp = client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token))
    return resp.get_json()["member"]


def _verified_volunteer(client, make_user, auth_header, admin_token, email="ach-vol@example.com"):
    user, access_token, _ = make_user(email=email, name="Achievement Volunteer")
    volunteers = client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"]
    vid = next(v for v in volunteers if v["email"] == email)["id"]
    client.patch(f"/api/volunteers/{vid}", json={"status": "Verified"}, headers=auth_header(admin_token))
    return user, access_token


def _complete_a_visit(app, client, admin_token, auth_header, vol, member_name):
    member = _register_member(client, admin_token, auth_header, name=member_name)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]
    # A real started->completed transition through the actual API, not a
    # DB shortcut — this is exactly the code path check_and_award is
    # wired into (homevisits/routes.py's update_visit).
    with app.app_context():
        row = db.session.get(HomeVisit, visit["id"])
        row.started_at = utcnow() - timedelta(minutes=30)
        db.session.commit()
    vol_token_visit = client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed"}, headers=auth_header(admin_token))
    return vol_token_visit.get_json()


# ---------- Automatic threshold awards ----------

def test_completing_first_visit_awards_first_visit_achievement(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    _complete_a_visit(app, client, admin_token, auth_header, vol, "Member One")

    achievements = client.get("/api/volunteers/me/achievements", headers=auth_header(vol_token)).get_json()["achievements"]
    codes = [e["achievement"]["code"] for e in achievements["earned"]]
    assert "first_visit" in codes


def test_ten_visits_awards_the_ten_visits_achievement(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    for i in range(10):
        _complete_a_visit(app, client, admin_token, auth_header, vol, f"Member {i}")

    achievements = client.get("/api/volunteers/me/achievements", headers=auth_header(vol_token)).get_json()["achievements"]
    codes = [e["achievement"]["code"] for e in achievements["earned"]]
    assert "first_visit" in codes
    assert "ten_visits" in codes
    assert "twenty_five_visits" not in codes  # not yet earned


def test_achievement_checker_is_idempotent_no_duplicate_on_repeated_completions(client, app, make_user, make_staff_user, auth_header):
    """Completing further visits after already crossing a threshold must
    never award the same achievement a second time."""
    _, admin_token = make_staff_user("admin")
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    _complete_a_visit(app, client, admin_token, auth_header, vol, "First")
    _complete_a_visit(app, client, admin_token, auth_header, vol, "Second")
    _complete_a_visit(app, client, admin_token, auth_header, vol, "Third")

    achievements = client.get("/api/volunteers/me/achievements", headers=auth_header(vol_token)).get_json()["achievements"]
    first_visit_awards = [e for e in achievements["earned"] if e["achievement"]["code"] == "first_visit"]
    assert len(first_visit_awards) == 1


def test_running_the_checker_function_directly_twice_never_duplicates(app, client, make_user, make_staff_user, auth_header):
    """Direct unit-level idempotency check on the service function itself,
    not just through the HTTP-triggered path."""
    from app.achievements.service import check_and_award
    from app.models import VolunteerAchievement

    _, admin_token = make_staff_user("admin")
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    _complete_a_visit(app, client, admin_token, auth_header, vol, "Direct Check")

    with app.app_context():
        from app.models import VolunteerProfile
        profile = VolunteerProfile.query.filter_by(user_id=vol["id"]).first()
        check_and_award(vol["id"], profile.id)
        check_and_award(vol["id"], profile.id)
        check_and_award(vol["id"], profile.id)
        db.session.commit()
        count = VolunteerAchievement.query.filter_by(volunteer_profile_id=profile.id, achievement_id=db.session.query(Achievement.id).filter_by(code="first_visit").scalar()).count()
        assert count == 1


def test_hours_achievement_awarded_when_service_minutes_cross_threshold(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _register_member(client, admin_token, auth_header)
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    visit = client.post("/api/home-visits", json={"elderly_member_id": member["id"], "assigned_to_id": vol["id"], **VALID_REASON}, headers=auth_header(admin_token)).get_json()["visit"]
    with app.app_context():
        row = db.session.get(HomeVisit, visit["id"])
        row.started_at = utcnow() - timedelta(hours=26)  # 1560 minutes >= 1500 (25h) threshold
        db.session.commit()
    client.patch(f"/api/home-visits/{visit['id']}", json={"status": "Completed"}, headers=auth_header(admin_token))

    achievements = client.get("/api/volunteers/me/achievements", headers=auth_header(vol_token)).get_json()["achievements"]
    codes = [e["achievement"]["code"] for e in achievements["earned"]]
    assert "hours_25" in codes


def test_upcoming_achievements_show_current_progress(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    _complete_a_visit(app, client, admin_token, auth_header, vol, "Progress Check")

    achievements = client.get("/api/volunteers/me/achievements", headers=auth_header(vol_token)).get_json()["achievements"]
    ten_visits = next(e for e in achievements["upcoming"] if e["code"] == "ten_visits")
    assert ten_visits["current_value"] == 1
    assert ten_visits["threshold_value"] == 10


def test_manual_only_achievements_are_never_in_upcoming_or_auto_awarded(client, app, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    vol, vol_token = _verified_volunteer(client, make_user, auth_header, admin_token)
    for i in range(10):
        _complete_a_visit(app, client, admin_token, auth_header, vol, f"M{i}")

    achievements = client.get("/api/volunteers/me/achievements", headers=auth_header(vol_token)).get_json()["achievements"]
    upcoming_codes = [e["code"] for e in achievements["upcoming"]]
    earned_codes = [e["achievement"]["code"] for e in achievements["earned"]]
    assert "volunteer_of_the_month" not in upcoming_codes
    assert "volunteer_of_the_month" not in earned_codes


# ---------- Recognition (manual awards) ----------

def test_admin_can_recognize_a_volunteer(client, make_user, make_staff_user, auth_header):
    user, vol_token, _ = make_user(email="recognize-me@example.com")
    _, admin_token = make_staff_user("admin")
    vid = next(v for v in client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"] if v["email"] == "recognize-me@example.com")["id"]
    achievement_id = next(a for a in _list_achievements(client, admin_token, auth_header) if a["code"] == "volunteer_of_the_month")["id"]

    resp = client.post(f"/api/volunteers/{vid}/recognition", json={"achievement_id": achievement_id, "notes": "Exceptional August"}, headers=auth_header(admin_token))
    assert resp.status_code == 201
    assert resp.get_json()["recognition"]["source"] == "manual"

    achievements = client.get("/api/volunteers/me/achievements", headers=auth_header(vol_token)).get_json()["achievements"]
    assert any(e["achievement"]["code"] == "volunteer_of_the_month" for e in achievements["earned"])

    notifications = client.get("/api/notifications", headers=auth_header(vol_token)).get_json()["notifications"]
    assert any(n["notification_type"] == "Achievement Awarded" for n in notifications)


def test_recognizing_the_same_volunteer_twice_with_the_same_award_conflicts(client, make_user, make_staff_user, auth_header):
    user, _, _ = make_user(email="doublerecognize@example.com")
    _, admin_token = make_staff_user("admin")
    vid = next(v for v in client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"] if v["email"] == "doublerecognize@example.com")["id"]
    achievement_id = next(a for a in _list_achievements(client, admin_token, auth_header) if a["code"] == "community_champion")["id"]

    client.post(f"/api/volunteers/{vid}/recognition", json={"achievement_id": achievement_id}, headers=auth_header(admin_token))
    resp = client.post(f"/api/volunteers/{vid}/recognition", json={"achievement_id": achievement_id}, headers=auth_header(admin_token))
    assert resp.status_code == 409


def test_cannot_manually_award_a_threshold_based_achievement(client, make_user, make_staff_user, auth_header):
    """Recognition is only for "manual" threshold_type achievements — a
    real, threshold-based one (like ten_visits) must never be handed out
    without the volunteer actually meeting it."""
    user, _, _ = make_user(email="cheatthreshold@example.com")
    _, admin_token = make_staff_user("admin")
    vid = next(v for v in client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"] if v["email"] == "cheatthreshold@example.com")["id"]
    achievement_id = next(a for a in _list_achievements(client, admin_token, auth_header) if a["code"] == "ten_visits")["id"]

    resp = client.post(f"/api/volunteers/{vid}/recognition", json={"achievement_id": achievement_id}, headers=auth_header(admin_token))
    assert resp.status_code == 400


def test_volunteer_cannot_award_themselves_recognition(client, make_user, auth_header):
    user, token, _ = make_user(email="selfrecognize@example.com")
    resp = client.post(f"/api/volunteers/{user['id']}/recognition", json={"achievement_id": 1}, headers=auth_header(token))
    assert resp.status_code == 403


def test_staff_can_also_recognize_a_volunteer(client, make_user, make_staff_user, auth_header):
    user, _, _ = make_user(email="staffrecognize@example.com")
    _, admin_token = make_staff_user("admin")
    _, staff_token = make_staff_user("staff", email="recognizer@example.com")
    vid = next(v for v in client.get("/api/volunteers", headers=auth_header(admin_token)).get_json()["volunteers"] if v["email"] == "staffrecognize@example.com")["id"]
    achievement_id = next(a for a in _list_achievements(client, admin_token, auth_header) if a["code"] == "outstanding_service")["id"]

    resp = client.post(f"/api/volunteers/{vid}/recognition", json={"achievement_id": achievement_id}, headers=auth_header(staff_token))
    assert resp.status_code == 201


def _list_achievements(client, admin_token, auth_header):
    return client.get("/api/achievements", headers=auth_header(admin_token)).get_json()["achievements"]


def test_unauthenticated_cannot_access_achievements(client):
    assert client.get("/api/volunteers/me/achievements").status_code == 401
