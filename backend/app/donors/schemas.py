from marshmallow import Schema, fields, validate

from ..models import DONOR_TYPES


class DonorCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    email = fields.Email(load_default=None, allow_none=True)
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=40))
    organization = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    donor_type = fields.String(load_default="Individual", validate=validate.OneOf(DONOR_TYPES))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class DonorUpdateSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=150))
    email = fields.Email(allow_none=True)
    phone = fields.String(allow_none=True, validate=validate.Length(max=40))
    organization = fields.String(allow_none=True, validate=validate.Length(max=150))
    donor_type = fields.String(validate=validate.OneOf(DONOR_TYPES))
    notes = fields.String(allow_none=True, validate=validate.Length(max=2000))
    active = fields.Boolean()
