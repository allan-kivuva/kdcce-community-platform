from ..extensions import db
from ..models import Notification


def notify(recipient_id, notification_type, title, message, related_resource_type=None, related_resource_id=None):
    """The single chokepoint every trigger site calls to create a
    notification. In-app delivery only for now — a future channel
    (email/SMS) wraps this same function later, so every call site stays
    unchanged when that happens. Does not commit; callers add this to the
    same db.session transaction as the action that triggered it, so the
    notification can never exist without (or drift from) the event that
    caused it — if the transaction rolls back, so does this."""
    notification = Notification(
        recipient_id=recipient_id,
        notification_type=notification_type,
        title=title,
        message=message,
        related_resource_type=related_resource_type,
        related_resource_id=related_resource_id,
    )
    db.session.add(notification)
    return notification
