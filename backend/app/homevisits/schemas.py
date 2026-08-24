from marshmallow import Schema, fields, validate

from ..models import HOME_VISIT_PRIORITIES, HOME_VISIT_STATUSES


class HomeVisitCreateSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    reason = fields.String(required=True, validate=validate.Length(min=1, max=2000))
    priority = fields.String(allow_none=False, validate=validate.OneOf(HOME_VISIT_PRIORITIES))
    assigned_to_id = fields.Integer(load_default=None, allow_none=True)
    scheduled_at = fields.DateTime(load_default=None, allow_none=True)


class HomeVisitStaffUpdateSchema(Schema):
    """Full edit — admin/staff only. No load_default on status/
    follow_up_required/priority: a meaningful non-null default only makes
    sense at creation, not on every partial edit that omits the field."""

    elderly_member_id = fields.Integer()
    assigned_to_id = fields.Integer(allow_none=True)
    priority = fields.String(allow_none=False, validate=validate.OneOf(HOME_VISIT_PRIORITIES))
    status = fields.String(allow_none=False, validate=validate.OneOf(HOME_VISIT_STATUSES))
    reason = fields.String(validate=validate.Length(min=1, max=2000))
    scheduled_at = fields.DateTime(allow_none=True)
    observations = fields.String(allow_none=True, validate=validate.Length(max=4000))
    support_provided = fields.String(allow_none=True, validate=validate.Length(max=2000))
    follow_up_required = fields.Boolean()
    follow_up_notes = fields.String(allow_none=True, validate=validate.Length(max=2000))


class HomeVisitAssigneeUpdateSchema(Schema):
    """What the assigned staff member or verified volunteer may record on
    their own visit — the outcome, not the assignment itself."""

    status = fields.String(allow_none=False, validate=validate.OneOf(HOME_VISIT_STATUSES))
    observations = fields.String(allow_none=True, validate=validate.Length(max=4000))
    support_provided = fields.String(allow_none=True, validate=validate.Length(max=2000))
    follow_up_required = fields.Boolean()
    follow_up_notes = fields.String(allow_none=True, validate=validate.Length(max=2000))
