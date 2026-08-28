from marshmallow import Schema, fields, validate

from ..models import VOLUNTEER_STATUSES


class VolunteerSelfUpdateSchema(Schema):
    """What a volunteer may change on their own profile/application — never
    status, reviewed_by, reviewed_at, or rejection_reason. Used both for
    the initial application (immediately after registration) and for later
    self-service edits — the same fields are editable either way."""

    phone = fields.String(allow_none=True, validate=validate.Length(max=40))
    skills = fields.String(allow_none=True, validate=validate.Length(max=1000))
    availability = fields.String(allow_none=True, validate=validate.Length(max=1000))
    areas_of_interest = fields.String(allow_none=True, validate=validate.Length(max=1000))
    experience = fields.String(allow_none=True, validate=validate.Length(max=2000))
    motivation = fields.String(allow_none=True, validate=validate.Length(max=2000))
    bio = fields.String(allow_none=True, validate=validate.Length(max=2000))


class VolunteerStaffUpdateSchema(VolunteerSelfUpdateSchema):
    """Staff/admin can additionally verify or reject a volunteer, and
    record why on a rejection. rejection_reason is accepted regardless of
    which way status is set — the route clears it on any non-Rejected
    status so a stale reason from a previous rejection can't linger past
    a later reversal."""

    status = fields.String(allow_none=False, validate=validate.OneOf(VOLUNTEER_STATUSES))
    rejection_reason = fields.String(allow_none=True, validate=validate.Length(max=2000))
