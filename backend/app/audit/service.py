import json
from decimal import Decimal

from ..extensions import db
from ..models import AuditLog


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def _serialize(snapshot):
    if snapshot is None:
        return None
    return json.dumps({k: _json_safe(v) for k, v in snapshot.items()}, default=str)


def log_action(actor_id, action, resource_type, resource_id, before=None, after=None):
    """The single chokepoint every sensitive financial write goes
    through — same "one function every call site calls" shape as
    notify(). `before`/`after` are small plain dicts of only the fields
    that matter for that action (never a raw request body, never
    anything payment-credential-shaped, since this app never collects
    those in the first place). Does not commit; the caller's route
    commits in the same transaction as the actual change, so an audit
    entry can never exist without (or drift from) the change it
    describes."""
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before=_serialize(before),
        after=_serialize(after),
    )
    db.session.add(entry)
    return entry
