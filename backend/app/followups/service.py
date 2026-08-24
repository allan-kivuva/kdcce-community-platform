from ..extensions import db
from ..models import FollowUp
from ..notifications.service import notify


def create_from_source(elderly_member_id, source_type, source_id, reason, created_by_id, assigned_to_id=None, priority="Medium"):
    """The single chokepoint every source module calls when
    follow_up_required transitions into True (see the callers in
    health/routes.py, homevisits/routes.py, assistance/routes.py,
    incidents/routes.py — each checks it's a real False->True transition,
    not just re-saving an already-True flag, before calling this).
    Defaults assigned_to_id to whoever's already handling that
    person/visit/request if the caller has one, otherwise it's
    unassigned for admin to triage."""
    followup = FollowUp(
        elderly_member_id=elderly_member_id,
        source_type=source_type,
        source_id=source_id,
        reason=reason or "Follow-up required",
        priority=priority,
        assigned_to_id=assigned_to_id,
        created_by_id=created_by_id,
    )
    db.session.add(followup)
    db.session.flush()
    if assigned_to_id:
        notify(
            assigned_to_id, "Follow-up Assigned", "New follow-up assigned to you",
            followup.reason,
            related_resource_type="follow_up", related_resource_id=followup.id,
        )
    return followup
