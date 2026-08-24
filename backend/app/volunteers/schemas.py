from marshmallow import Schema, fields, validate

from ..models import VOLUNTEER_STATUSES


class VolunteerSelfUpdateSchema(Schema):
    """What a volunteer may change on their own profile — never status."""

    phone = fields.String(allow_none=True, validate=validate.Length(max=40))
    skills = fields.String(allow_none=True, validate=validate.Length(max=1000))
    availability = fields.String(allow_none=True, validate=validate.Length(max=1000))
    bio = fields.String(allow_none=True, validate=validate.Length(max=2000))


class VolunteerStaffUpdateSchema(VolunteerSelfUpdateSchema):
    """Staff/admin can additionally verify or reject a volunteer."""

    status = fields.String(allow_none=False, validate=validate.OneOf(VOLUNTEER_STATUSES))
