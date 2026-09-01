from datetime import timedelta, timezone

from ..models import AssistanceRequest, HomeVisit, VolunteerHours, utcnow


def _as_naive_utc(dt):
    """SQLite (this app's dev/test database) does not reliably round-trip
    a DateTime(timezone=True) column's tzinfo — a value just assigned in
    Python this request is timezone-aware, but the identical column
    re-loaded fresh from the database (a different request, or after a
    flush/expire) comes back naive. Every started_at/completed_at pair
    subtracted below can independently be either, so both sides are
    normalized to naive UTC first — the only shape immune to Python
    raising "can't subtract offset-naive and offset-aware datetimes"
    regardless of which one(s) happened to keep their tzinfo."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo is not None else dt


def _assignment_minutes(assignment):
    """Minutes for one completed assignment, or 0 if it doesn't actually
    qualify. Guards against exactly the failure modes called out for this
    feature:
    - incomplete (no started_at/completed_at, or status isn't Completed
      at all) -> 0, never counted as service hours.
    - a negative/zero duration (a bad completed_at < started_at, however
      that happened) -> 0, never accepted as real time served.
    Integer minutes via floor division, never a float — matches this
    model's "store minutes, not fractional hours" principle."""
    if assignment.status != "Completed" or assignment.started_at is None or assignment.completed_at is None:
        return 0
    delta = _as_naive_utc(assignment.completed_at) - _as_naive_utc(assignment.started_at)
    if delta <= timedelta(0):
        return 0
    return int(delta.total_seconds() // 60)


def automatic_entries(user_id, since=None, until=None):
    """Real per-assignment entries derived live from HomeVisit/
    AssistanceRequest — never stored, never duplicated (each completed
    assignment is read and summed exactly once, from its own two
    columns). `since`/`until` optionally bound by completed_at.

    Takes the assignee's USER id, not a volunteer_profile_id — HomeVisit.
    assigned_to_id/AssistanceRequest.assigned_to_id are both FKs to
    users.id (staff/admin can be assignees too, not just volunteers), so
    that's what this queries by. Every caller in this module already has
    both ids on hand and passes each function the one it actually needs."""
    visits_q = HomeVisit.query.filter(HomeVisit.assigned_to_id == user_id, HomeVisit.status == "Completed")
    requests_q = AssistanceRequest.query.filter(AssistanceRequest.assigned_to_id == user_id, AssistanceRequest.status == "Completed")
    if since is not None:
        visits_q = visits_q.filter(HomeVisit.completed_at >= since)
        requests_q = requests_q.filter(AssistanceRequest.completed_at >= since)
    if until is not None:
        visits_q = visits_q.filter(HomeVisit.completed_at <= until)
        requests_q = requests_q.filter(AssistanceRequest.completed_at <= until)

    entries = []
    for v in visits_q.all():
        minutes = _assignment_minutes(v)
        if minutes > 0:
            entries.append({
                "kind": "home_visit", "id": v.id, "date": v.completed_at.date().isoformat(),
                "minutes": minutes, "label": f"Home visit — {v.elderly_member.full_name}",
            })
    for r in requests_q.all():
        minutes = _assignment_minutes(r)
        if minutes > 0:
            entries.append({
                "kind": "assistance_request", "id": r.id, "date": r.completed_at.date().isoformat(),
                "minutes": minutes, "label": f"Assistance — {r.elderly_member.full_name}",
            })
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def automatic_minutes(user_id, since=None, until=None):
    return sum(e["minutes"] for e in automatic_entries(user_id, since, until))


def approved_manual_minutes(volunteer_profile_id, since=None, until=None):
    query = VolunteerHours.query.filter(VolunteerHours.volunteer_profile_id == volunteer_profile_id, VolunteerHours.status == "Approved")
    if since is not None:
        query = query.filter(VolunteerHours.date >= since)
    if until is not None:
        query = query.filter(VolunteerHours.date <= until)
    return sum(row.duration_minutes for row in query.all())


def total_minutes(user_id, volunteer_profile_id, since=None, until=None):
    """Combined automatic (by user id, via assignment assignee) + approved
    manual (by volunteer_profile_id) minutes for one window. Both halves
    are real, already-committed data — nothing estimated."""
    return automatic_minutes(user_id, since, until) + approved_manual_minutes(volunteer_profile_id, since, until)


def summary(user_id, volunteer_profile_id):
    """The full hours-summary shape used by both the volunteer's own view
    and the admin/staff view of one volunteer — today / this week / this
    month / lifetime, each combining automatic + approved-manual minutes,
    plus the most recent individual entries (both kinds interleaved) for
    a "recent activity" list."""
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    manual_entries = [
        {"kind": "manual", "id": h.id, "date": h.date.isoformat(), "minutes": h.duration_minutes, "label": h.category, "status": h.status}
        for h in VolunteerHours.query.filter_by(volunteer_profile_id=volunteer_profile_id).order_by(VolunteerHours.date.desc()).limit(10).all()
    ]
    auto_entries = automatic_entries(user_id)[:10]
    recent = sorted(manual_entries + auto_entries, key=lambda e: e["date"], reverse=True)[:10]

    return {
        "minutes_today": total_minutes(user_id, volunteer_profile_id, since=today_start),
        "minutes_this_week": total_minutes(user_id, volunteer_profile_id, since=week_start),
        "minutes_this_month": total_minutes(user_id, volunteer_profile_id, since=month_start),
        "minutes_lifetime": total_minutes(user_id, volunteer_profile_id),
        "automatic_minutes_lifetime": automatic_minutes(user_id),
        "approved_manual_minutes_lifetime": approved_manual_minutes(volunteer_profile_id),
        "recent_entries": recent,
    }
