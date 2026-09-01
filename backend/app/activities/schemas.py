from marshmallow import Schema, fields, validate

from ..models import (
    ACTIVITY_PARTICIPANT_STATUSES, ACTIVITY_STATUSES, ACTIVITY_TYPES,
    ACTIVITY_VOLUNTEER_ROLES, ACTIVITY_VOLUNTEER_STATUSES,
)


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
    program_id = fields.Integer(load_default=None, allow_none=True)
    capacity = fields.Integer(load_default=None, allow_none=True, validate=validate.Range(min=1))
    registration_open = fields.Boolean(load_default=True)
    registration_deadline = fields.DateTime(load_default=None, allow_none=True)


class ActivityParticipantSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))


class ActivityParticipantUpdateSchema(Schema):
    status = fields.String(required=True, validate=validate.OneOf(ACTIVITY_PARTICIPANT_STATUSES))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))


class ActivityVolunteerAssignSchema(Schema):
    """Staff assigning a specific volunteer to a specific role — distinct
    from RSVP (see routes.py's self-RSVP endpoint), which has no role
    choice and always defaults to "General Volunteer"."""

    volunteer_id = fields.Integer(required=True)
    role = fields.String(load_default="General Volunteer", validate=validate.OneOf(ACTIVITY_VOLUNTEER_ROLES))


class ActivityVolunteerUpdateSchema(Schema):
    """Full admin/staff edit of one staffing row — role, status, and
    check-in/out. No load_default on any field: a partial PATCH must
    never silently reset a field it didn't mention."""

    role = fields.String(validate=validate.OneOf(ACTIVITY_VOLUNTEER_ROLES))
    status = fields.String(validate=validate.OneOf(ACTIVITY_VOLUNTEER_STATUSES))
    checked_in = fields.Boolean()
    checked_out = fields.Boolean()


class ActivityVolunteerSelfResponseSchema(Schema):
    """The narrow self-service action a volunteer may take on their own
    staffing assignment — confirm or decline it. Nothing else: not the
    role, not attendance, not another volunteer's row (enforced in
    routes.py, not just by this schema's shape)."""

    status = fields.String(required=True, validate=validate.OneOf(("Confirmed", "Declined")))
