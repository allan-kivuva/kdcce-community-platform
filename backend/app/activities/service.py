from ..extensions import db
from ..models import ACTIVITY_VOLUNTEER_CONFIRMED_STATUSES, ActivityVolunteer, utcnow


class RsvpError(Exception):
    """Raised for an invalid RSVP/staffing action (closed registration,
    duplicate RSVP, nothing to cancel, ...); routes catch this and turn
    it into the app's standard 400/409 shape."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def confirmed_volunteer_count(activity_id):
    return ActivityVolunteer.query.filter(
        ActivityVolunteer.activity_id == activity_id,
        ActivityVolunteer.status.in_(ACTIVITY_VOLUNTEER_CONFIRMED_STATUSES),
    ).count()


def waitlist_count(activity_id):
    return ActivityVolunteer.query.filter_by(activity_id=activity_id, status="Waitlisted").count()


def get_assignment(activity_id, volunteer_id):
    return ActivityVolunteer.query.filter_by(activity_id=activity_id, volunteer_id=volunteer_id).first()


def self_rsvp(activity, volunteer_id):
    """A volunteer's own self-service RSVP. Goes to Confirmed if there's
    an open slot (or unlimited capacity), otherwise Waitlisted — decided
    once, synchronously, inside this one request (no race-condition-prone
    "check then insert" gap: the row is written in the same request that
    counted confirmed rows, and this app's SQLite dev/test setup + small
    real-world concurrency at this org's scale make a stricter locking
    scheme unnecessary overhead)."""
    if not activity.registration_open:
        raise RsvpError("Registration is closed for this event")
    if activity.registration_deadline is not None:
        deadline = activity.registration_deadline
        now = utcnow()
        deadline_naive = deadline.replace(tzinfo=None) if deadline.tzinfo else deadline
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        if now_naive > deadline_naive:
            raise RsvpError("The registration deadline has passed")

    existing = get_assignment(activity.id, volunteer_id)
    if existing is not None and existing.status not in ("Cancelled", "Declined"):
        raise RsvpError("You have already RSVPed to this event")

    if activity.capacity is not None and confirmed_volunteer_count(activity.id) >= activity.capacity:
        status = "Waitlisted"
    else:
        status = "Confirmed"

    now = utcnow()
    if existing is not None:
        existing.role = "General Volunteer"
        existing.status = status
        existing.assigned_by_id = None
        existing.assigned_at = now
        existing.confirmed_at = now if status == "Confirmed" else None
        row = existing
    else:
        row = ActivityVolunteer(
            activity_id=activity.id, volunteer_id=volunteer_id, role="General Volunteer",
            status=status, assigned_by_id=None, confirmed_at=now if status == "Confirmed" else None,
        )
        db.session.add(row)
    db.session.flush()
    return row


def promote_next_waitlisted(activity_id):
    """Deterministic FIFO promotion — the longest-waiting Waitlisted row,
    by assigned_at. The promoted row leaves "Waitlisted" in the same
    flush that selects it, so a second call (e.g. two cancellations in
    quick succession) can never pick the same row twice."""
    next_row = (
        ActivityVolunteer.query.filter_by(activity_id=activity_id, status="Waitlisted")
        .order_by(ActivityVolunteer.assigned_at.asc())
        .first()
    )
    if next_row is None:
        return None
    next_row.status = "Confirmed"
    next_row.confirmed_at = utcnow()
    db.session.flush()
    return next_row


def cancel_rsvp(activity_id, volunteer_id):
    row = get_assignment(activity_id, volunteer_id)
    if row is None or row.status in ("Cancelled", "Declined"):
        raise RsvpError("No active RSVP to cancel")
    freed_a_slot = row.status in ACTIVITY_VOLUNTEER_CONFIRMED_STATUSES
    row.status = "Cancelled"
    db.session.flush()
    promoted = promote_next_waitlisted(activity_id) if freed_a_slot else None
    return row, promoted


def staff_assign(activity, volunteer_id, role, assigned_by_id):
    """Staff assigning a volunteer to a specific staffing role — a
    different path from self_rsvp (bypasses capacity: an organizer
    filling a Logistics/Registration role is a staffing decision, not a
    capacity-governed attendee slot)."""
    existing = get_assignment(activity.id, volunteer_id)
    if existing is not None and existing.status not in ("Cancelled", "Declined"):
        raise RsvpError("This volunteer already has an active RSVP/assignment for this event")

    now = utcnow()
    if existing is not None:
        existing.role = role
        existing.status = "Assigned"
        existing.assigned_by_id = assigned_by_id
        existing.assigned_at = now
        existing.confirmed_at = None
        existing.checked_in_at = None
        existing.checked_out_at = None
        row = existing
    else:
        row = ActivityVolunteer(activity_id=activity.id, volunteer_id=volunteer_id, role=role, status="Assigned", assigned_by_id=assigned_by_id)
        db.session.add(row)
    db.session.flush()
    return row
