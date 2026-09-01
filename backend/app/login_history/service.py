from flask import request

from ..extensions import db
from ..models import LoginHistory


def record_attempt(user, attempted_email, success, failure_reason=None):
    """The one chokepoint every login-related route goes through to
    record an attempt — same shape as audit.service.log_action and
    notifications.service.notify. Never passed a password. Does not
    commit; the caller's route commits in the same transaction."""
    entry = LoginHistory(
        user_id=user.id if user else None,
        attempted_email=attempted_email,
        success=success,
        ip_address=request.remote_addr,
        user_agent=(request.headers.get("User-Agent") or "")[:255],
        failure_reason=failure_reason,
    )
    db.session.add(entry)
    return entry
