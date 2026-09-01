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
    # No load_default, same reasoning as every other field in this shared
    # create+PATCH schema (see class docstring) — on create, an omitted
    # assigned_to_id should simply not be in `data` at all (the column is
    # nullable with no explicit default, so the row is created unassigned
    # either way); giving it load_default=None here would make it ALSO
    # apply on a partial PATCH that doesn't mention this field at all,
    # silently wiping out an existing assignment on an unrelated edit.
    assigned_to_id = fields.Integer(allow_none=True)
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


class IncidentVolunteerCreateSchema(Schema):
    """What a verified volunteer may submit as a "Report a Concern" —
    deliberately a much smaller field set than IncidentSchema: no status,
    resolution_notes, emergency_contact_notified/_at, or occurred_at — those
    stay staff/admin-set (occurred_at defaults to "now" server-side, same
    "don't trust client timestamps" principle as every started_at/
    completed_at in this app). elderly_member_id is optional ("if
    applicable") and deliberately NOT restricted to members assigned to the
    reporting volunteer — a concern report is a safeguarding tool, and
    narrowing who can be reported on would only add friction to exactly the
    reports that most need to go through."""

    elderly_member_id = fields.Integer(load_default=None, allow_none=True)
    incident_type = fields.String(required=True, validate=validate.OneOf(INCIDENT_TYPES))
    severity = fields.String(required=True, validate=validate.OneOf(INCIDENT_SEVERITIES))
    description = fields.String(required=True, validate=validate.Length(min=1, max=4000))
    immediate_action_taken = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    follow_up_required = fields.Boolean(load_default=False)
    follow_up_notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
