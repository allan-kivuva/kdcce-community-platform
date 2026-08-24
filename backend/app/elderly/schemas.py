from marshmallow import Schema, fields, validate

from ..models import ELDERLY_GENDERS, ELDERLY_STATUSES


class OPASchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    location = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class ElderlyMemberSchema(Schema):
    full_name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    date_of_birth = fields.Date(load_default=None, allow_none=True)
    gender = fields.String(required=True, validate=validate.OneOf(ELDERLY_GENDERS))
    location = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    opa_id = fields.Integer(load_default=None, allow_none=True)
    emergency_contact_name = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=120))
    emergency_contact_phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=40))
    emergency_contact_relationship = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=60))
    vulnerability_notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=4000))
    health_notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=4000))
    allergies = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    dietary_requirements = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    status = fields.String(load_default="Active", validate=validate.OneOf(ELDERLY_STATUSES))
