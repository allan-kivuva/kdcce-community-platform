from ..announcements.service import resolve_audience_users
from ..extensions import db
from ..models import Broadcast
from ..notifications.service import notify


def create_broadcast(sender_id, audience_type, title, message, selected_user_ids=None, client_token=None):
    """Fan out a one-off message to a resolved audience via the existing
    notify() chokepoint — reuses announcements.service's audience
    resolution rather than a second copy of the same role/status logic.

    Returns (broadcast, created) — `created` is False when `client_token`
    matches an already-recorded broadcast, so a retried submit (double
    click, a network retry) returns the original send instead of
    notifying the whole audience a second time."""
    if client_token:
        existing = Broadcast.query.filter_by(client_token=client_token).first()
        if existing is not None:
            return existing, False

    recipients = [u for u in resolve_audience_users(audience_type, selected_user_ids) if u.id != sender_id]

    broadcast = Broadcast(
        sender_id=sender_id,
        audience_type=audience_type,
        audience_detail=",".join(str(uid) for uid in selected_user_ids) if audience_type == "Selected" and selected_user_ids else None,
        title=title,
        message=message,
        recipient_count=len(recipients),
        client_token=client_token,
    )
    db.session.add(broadcast)
    db.session.flush()

    for user in recipients:
        notify(
            user.id, "Broadcast Message", title, message,
            related_resource_type="broadcast", related_resource_id=broadcast.id,
        )
    return broadcast, True
