from marshmallow import Schema, fields, validate

from ..models import ASSISTANCE_PRIORITIES, ASSISTANCE_STATUSES, ASSISTANCE_TYPES

# What the assigned user may set their own request's status to via PATCH.
# "Accepted" is deliberately excluded — that's POST .../accept, a separate,
# narrower action (see routes.py) — and "Requested"/"Matching"/"Assigned"
# are staff-only states the assignee has no business setting.
ASSIGNEE_SETTABLE_STATUSES = ("Started", "In Progress", "Completed", "Cancelled")


class AssistanceRequestCreateSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    request_type = fields.String(required=True, validate=validate.OneOf(ASSISTANCE_TYPES))
    description = fields.String(required=True, validate=validate.Length(min=1, max=2000))
    priority = fields.String(allow_none=False, validate=validate.OneOf(ASSISTANCE_PRIORITIES))
    assigned_to_id = fields.Integer(load_default=None, allow_none=True)
    home_visit_id = fields.Integer(load_default=None, allow_none=True)
    scheduled_at = fields.DateTime(load_default=None, allow_none=True)


class AssistanceRequestStaffUpdateSchema(Schema):
    """Full edit — admin/staff only. No load_default on status/priority:
    a meaningful non-null default only applies at creation."""

    elderly_member_id = fields.Integer()
    assigned_to_id = fields.Integer(allow_none=True)
    home_visit_id = fields.Integer(allow_none=True)
    request_type = fields.String(validate=validate.OneOf(ASSISTANCE_TYPES))
    priority = fields.String(allow_none=False, validate=validate.OneOf(ASSISTANCE_PRIORITIES))
    status = fields.String(allow_none=False, validate=validate.OneOf(ASSISTANCE_STATUSES))
    description = fields.String(validate=validate.Length(min=1, max=2000))
    scheduled_at = fields.DateTime(allow_none=True)
    outcome_notes = fields.String(allow_none=True, validate=validate.Length(max=2000))
    follow_up_required = fields.Boolean()
    follow_up_notes = fields.String(allow_none=True, validate=validate.Length(max=2000))


class AssistanceRequestAssigneeUpdateSchema(Schema):
    """What the assigned staff member or verified volunteer may record on
    their own request — the outcome, not the assignment itself."""

    status = fields.String(allow_none=False, validate=validate.OneOf(ASSIGNEE_SETTABLE_STATUSES))
    outcome_notes = fields.String(allow_none=True, validate=validate.Length(max=2000))
    follow_up_required = fields.Boolean()
    follow_up_notes = fields.String(allow_none=True, validate=validate.Length(max=2000))
