from datetime import timezone

from ..extensions import db
from ..models import Announcement, AnnouncementRecipient, User, VolunteerProfile, utcnow
from ..notifications.service import notify


def _as_naive_utc(dt):
    """SQLite does not reliably round-trip a DateTime(timezone=True)
    column's tzinfo across a session boundary — see the identical helper
    in volunteer_hours/service.py. Applied here so publish_at/expires_at
    comparisons against a freshly-computed `now` never depend on which
    side happened to keep its tzinfo."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo is not None else dt


def resolve_audience_users(audience_type, selected_user_ids=None):
    """A concrete list of User rows for `audience_type` — used both to
    fan out broadcast notifications immediately and (via
    _applies_to_user below) to decide, per viewer, whether one
    announcement is relevant to them."""
    if audience_type == "All":
        # Predates the family role and always meant "everyone
        # operational" — family is reached only via the explicit
        # "Family" audience below, never bundled into "All".
        return User.query.filter(User.role != "family").all()
    if audience_type == "Family":
        return User.query.filter_by(role="family").all()
    if audience_type == "Volunteers":
        return User.query.filter_by(role="volunteer").all()
    if audience_type == "Verified Volunteers":
        return (
            db.session.query(User)
            .join(VolunteerProfile, VolunteerProfile.user_id == User.id)
            .filter(VolunteerProfile.status == "Verified")
            .all()
        )
    if audience_type == "Staff":
        return User.query.filter_by(role="staff").all()
    if audience_type == "Admin":
        return User.query.filter_by(role="admin").all()
    if audience_type == "Selected":
        ids = selected_user_ids or []
        return User.query.filter(User.id.in_(ids)).all()
    return []


def _applies_to_user(announcement, user):
    t = announcement.audience_type
    if t == "All":
        return user.role != "family"
    if t == "Family":
        return user.role == "family"
    if t == "Volunteers":
        return user.role == "volunteer"
    if t == "Verified Volunteers":
        if user.role != "volunteer":
            return False
        profile = VolunteerProfile.query.filter_by(user_id=user.id).first()
        return profile is not None and profile.status == "Verified"
    if t == "Staff":
        return user.role == "staff"
    if t == "Admin":
        return user.role == "admin"
    if t == "Selected":
        return AnnouncementRecipient.query.filter_by(announcement_id=announcement.id, user_id=user.id).first() is not None
    return False


def _is_live(announcement, now):
    if not announcement.active:
        return False
    now = _as_naive_utc(now)
    if announcement.publish_at is not None and _as_naive_utc(announcement.publish_at) > now:
        return False
    if announcement.expires_at is not None and _as_naive_utc(announcement.expires_at) <= now:
        return False
    return True


def list_active_announcements_for_user(user):
    """Every announcement currently live (active, published, not yet
    expired) AND targeted at this user — visibility is computed fresh on
    every call from publish_at/expires_at/active, never a cached flag
    that could go stale relative to the clock."""
    now = utcnow()
    candidates = Announcement.query.filter(Announcement.active.is_(True)).order_by(Announcement.created_at.desc()).all()
    return [a for a in candidates if _is_live(a, now) and _applies_to_user(a, user)]


def _notify_audience(announcement):
    notification_type = "Urgent Announcement" if announcement.priority == "Urgent" else "Announcement"
    selected_ids = [r.user_id for r in announcement.recipients] if announcement.audience_type == "Selected" else None
    for user in resolve_audience_users(announcement.audience_type, selected_ids):
        if user.id == announcement.created_by_id:
            continue
        notify(
            user.id, notification_type, announcement.title, announcement.body[:200],
            related_resource_type="announcement", related_resource_id=announcement.id,
        )


def create_announcement(created_by_id, data):
    announcement = Announcement(
        title=data["title"],
        body=data["body"],
        priority=data.get("priority") or "Normal",
        audience_type=data["audience_type"],
        created_by_id=created_by_id,
        publish_at=data.get("publish_at"),
        expires_at=data.get("expires_at"),
        active=True,
    )
    db.session.add(announcement)
    db.session.flush()

    if announcement.audience_type == "Selected":
        for user_id in data.get("selected_user_ids") or []:
            db.session.add(AnnouncementRecipient(announcement_id=announcement.id, user_id=user_id))
        db.session.flush()

    # Only fan out immediately if this announcement is already live —
    # a future-dated (scheduled) one is not pushed now. There is no
    # background scheduler in this app (deliberately, per this phase's
    # "no WebSockets, no new heavy infra" constraint), so a scheduled
    # announcement becomes visible to a viewer once its publish_at
    # passes and they query the list, but no proactive notification
    # fires for it at that later moment — a documented limitation, not
    # an oversight.
    now = utcnow()
    if announcement.publish_at is None or _as_naive_utc(announcement.publish_at) <= _as_naive_utc(now):
        _notify_audience(announcement)
    return announcement


def update_announcement(announcement, data):
    for field in ("title", "body", "priority", "publish_at", "expires_at", "active"):
        if field in data:
            setattr(announcement, field, data[field])
    if "audience_type" in data:
        announcement.audience_type = data["audience_type"]
    if "selected_user_ids" in data:
        AnnouncementRecipient.query.filter_by(announcement_id=announcement.id).delete()
        if announcement.audience_type == "Selected":
            for user_id in data["selected_user_ids"] or []:
                db.session.add(AnnouncementRecipient(announcement_id=announcement.id, user_id=user_id))
    return announcement
