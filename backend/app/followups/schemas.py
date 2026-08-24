from marshmallow import Schema, fields, validate

from ..models import FOLLOW_UP_PRIORITIES, FOLLOW_UP_STATUSES


class FollowUpCreateSchema(Schema):
    """Manual creation — most follow-ups are auto-created by the source
    module (see service.py's create_from_source), but staff can also open
    one directly without an existing source record (e.g. a phone call
    from a family member flagging a concern)."""

    elderly_member_id = fields.Integer(required=True)
    reason = fields.String(required=True, validate=validate.Length(min=1, max=2000))
    priority = fields.String(load_default="Medium", validate=validate.OneOf(FOLLOW_UP_PRIORITIES))
    assigned_to_id = fields.Integer(load_default=None, allow_none=True)
    due_date = fields.Date(load_default=None, allow_none=True)
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class FollowUpUpdateSchema(Schema):
    """No load_default on status/priority: a meaningful non-null default
    only applies at creation, never on a partial edit that omits the
    field — same discipline as every other module's staff-update schema."""

    priority = fields.String(allow_none=False, validate=validate.OneOf(FOLLOW_UP_PRIORITIES))
    assigned_to_id = fields.Integer(allow_none=True)
    due_date = fields.Date(allow_none=True)
    status = fields.String(allow_none=False, validate=validate.OneOf(FOLLOW_UP_STATUSES))
    notes = fields.String(allow_none=True, validate=validate.Length(max=2000))
