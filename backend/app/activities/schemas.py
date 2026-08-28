from marshmallow import Schema, fields, validate

from ..models import ACTIVITY_PARTICIPANT_STATUSES, ACTIVITY_STATUSES, ACTIVITY_TYPES


class ActivitySchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=150))
    activity_type = fields.String(required=True, validate=validate.OneOf(ACTIVITY_TYPES))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    location = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    scheduled_at = fields.DateTime(required=True)
    facilitator_id = fields.Integer(load_default=None, allow_none=True)
    # No load_default on status: a meaningful non-null default only makes
    # sense at creation (handled in the route), not on every partial edit
    # that happens to omit it.
    status = fields.String(allow_none=False, validate=validate.OneOf(ACTIVITY_STATUSES))


class ActivityParticipantSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))


class ActivityParticipantUpdateSchema(Schema):
    status = fields.String(required=True, validate=validate.OneOf(ACTIVITY_PARTICIPANT_STATUSES))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))
