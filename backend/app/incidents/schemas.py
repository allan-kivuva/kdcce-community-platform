from marshmallow import Schema, fields, validate

from ..models import INCIDENT_SEVERITIES, INCIDENT_STATUSES, INCIDENT_TYPES


class IncidentSchema(Schema):
    """Used for both create (required=True fields) and PATCH
    (partial=True — required is then skipped). No load_default on any
    field with a meaningful non-null default (occurred_at,
    emergency_contact_notified, follow_up_required, status, severity): a
    default only applies at creation (handled in the route), never on a
    partial edit that happens to omit the field."""

    elderly_member_id = fields.Integer(required=True)
    incident_type = fields.String(required=True, validate=validate.OneOf(INCIDENT_TYPES))
    severity = fields.String(allow_none=False, validate=validate.OneOf(INCIDENT_SEVERITIES))
    occurred_at = fields.DateTime(allow_none=False)
    location = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    description = fields.String(required=True, validate=validate.Length(min=1, max=4000))
    immediate_action_taken = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    emergency_contact_notified = fields.Boolean(allow_none=False)
    emergency_contact_notified_at = fields.DateTime(load_default=None, allow_none=True)
    follow_up_required = fields.Boolean(allow_none=False)
    follow_up_notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    status = fields.String(allow_none=False, validate=validate.OneOf(INCIDENT_STATUSES))
    resolution_notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
