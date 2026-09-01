from datetime import date, datetime, timedelta, timezone


def _member(client, token, auth_header, name="Test Member"):
    return client.post("/api/elderly", json={"full_name": name, "gender": "Female"}, headers=auth_header(token)).get_json()["member"]


def _incident(client, token, auth_header, member_id, description="Fell near the dining hall", severity="High"):
    resp = client.post(
        "/api/incidents",
        json={"elderly_member_id": member_id, "incident_type": "Fall", "severity": severity, "occurred_at": datetime.now(timezone.utc).isoformat(), "description": description},
        headers=auth_header(token),
    )
    return resp.get_json()["incident"]


def test_concern_summary_cites_real_incident_and_is_labeled(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    incident = _incident(client, token, auth_header, member["id"], description="Member reported dizziness and fell.")

    resp = client.post(f"/api/ai/concerns/{incident['id']}/summary", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ai_generated"] is True
    assert body["human_review_required"] is True
    assert incident["id"] in body["source_resource_ids"]
    assert str(incident["id"]) in body["summary"] or "Fall" in body["summary"]


def test_concern_summary_never_changes_the_incident(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    incident = _incident(client, token, auth_header, member["id"])

    client.post(f"/api/ai/concerns/{incident['id']}/summary", headers=auth_header(token))

    refreshed = client.get(f"/api/incidents/{incident['id']}", headers=auth_header(token)).get_json()["incident"]
    assert refreshed["status"] == "Open"
    assert refreshed["severity"] == incident["severity"]
    assert refreshed["assigned_to_id"] == incident["assigned_to_id"]


def test_concern_summary_includes_follow_up_history(client, make_staff_user, auth_header):
    """create_from_source() (see incidents/routes.py's follow_up_required
    handling) is what actually links a FollowUp to an incident via
    source_type/source_id — there's no public API to fabricate that
    link directly (manual follow-up creation always sets
    source_type="manual"), so this exercises the real path: marking the
    incident's follow_up_required flag creates the linked FollowUp."""
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    incident_resp = client.post(
        "/api/incidents",
        json={
            "elderly_member_id": member["id"], "incident_type": "Fall", "severity": "High",
            "occurred_at": datetime.now(timezone.utc).isoformat(), "description": "Fell near the dining hall",
            "follow_up_required": True, "follow_up_notes": "Contact family",
        },
        headers=auth_header(token),
    )
    incident = incident_resp.get_json()["incident"]

    resp = client.post(f"/api/ai/concerns/{incident['id']}/summary", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["incident_id"] == incident["id"]


def test_concern_summary_unrelated_member_not_referenced(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member_a = _member(client, token, auth_header, "Member A")
    member_b = _member(client, token, auth_header, "Member B")
    incident = _incident(client, token, auth_header, member_a["id"])

    resp = client.post(f"/api/ai/concerns/{incident['id']}/summary", headers=auth_header(token))
    assert "Member B" not in resp.get_data(as_text=True)


def test_concern_summary_family_forbidden(client, make_staff_user, auth_header):
    """Phase 9 deliberately does not extend AI to family accounts at all
    — a concern summary is admin/staff-only internal content."""
    _, admin_token = make_staff_user("admin")
    member = _member(client, admin_token, auth_header)
    incident = _incident(client, admin_token, auth_header, member["id"])
    _, family_token = make_staff_user("family", email="famcs@example.com")
    resp = client.post(f"/api/ai/concerns/{incident['id']}/summary", headers=auth_header(family_token))
    assert resp.status_code == 403


def test_concern_summary_permissions(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _member(client, admin_token, auth_header)
    incident = _incident(client, admin_token, auth_header, member["id"])

    _, vol_token, _ = make_user()
    assert client.post(f"/api/ai/concerns/{incident['id']}/summary", headers=auth_header(vol_token)).status_code == 403
    assert client.post(f"/api/ai/concerns/{incident['id']}/summary").status_code == 401


def test_concern_summary_nonexistent_incident_404(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/concerns/999999/summary", headers=auth_header(token))
    assert resp.status_code == 404


def test_concern_summary_is_audited(client, make_staff_user, auth_header, app):
    from app.models import AIQueryLog

    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    incident = _incident(client, token, auth_header, member["id"])
    client.post(f"/api/ai/concerns/{incident['id']}/summary", headers=auth_header(token))

    with app.app_context():
        rows = AIQueryLog.query.filter_by(feature="concern_summary").all()
        assert len(rows) == 1
        assert incident["id"] in rows[0].to_dict()["resource_ids"]


# ---------- Timeline summaries ----------

def test_timeline_summary_default_30_days(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    _incident(client, token, auth_header, member["id"])

    resp = client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={}, headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["member_id"] == member["id"]
    assert "1 concern" in body["summary"] or "Test Member" in body["summary"]


def test_timeline_summary_empty_period_says_so(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    resp = client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={"days": 7}, headers=auth_header(token))
    assert "No recorded activity" in resp.get_json()["summary"]


def test_timeline_summary_custom_range(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    since = (date.today() - timedelta(days=10)).isoformat()
    until = date.today().isoformat()
    resp = client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={"since": since, "until": until}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["since"] == since
    assert resp.get_json()["until"] == until


def test_timeline_summary_custom_range_rejects_until_before_since(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    resp = client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={"since": "2026-06-01", "until": "2026-01-01"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_timeline_summary_custom_range_rejects_oversized_span(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    resp = client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={"since": "2020-01-01", "until": "2026-01-01"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_timeline_summary_invalid_days_rejected(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = _member(client, token, auth_header)
    resp = client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={"days": 45}, headers=auth_header(token))
    assert resp.status_code == 400


def test_timeline_summary_permissions(client, make_user, make_staff_user, auth_header):
    _, admin_token = make_staff_user("admin")
    member = _member(client, admin_token, auth_header)

    _, vol_token, _ = make_user()
    assert client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={}, headers=auth_header(vol_token)).status_code == 403
    assert client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={}).status_code == 401


def test_timeline_summary_family_forbidden(client, make_staff_user, auth_header):
    """Phase 9 explicitly does not extend AI features to family accounts
    — family summaries were deliberately left out this phase."""
    _, admin_token = make_staff_user("admin")
    member = _member(client, admin_token, auth_header)
    _, family_token = make_staff_user("family", email="famtl@example.com")
    resp = client.post(f"/api/ai/elderly/{member['id']}/timeline-summary", json={}, headers=auth_header(family_token))
    assert resp.status_code == 403


def test_timeline_summary_nonexistent_member_404(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/ai/elderly/999999/timeline-summary", json={}, headers=auth_header(token))
    assert resp.status_code == 404
