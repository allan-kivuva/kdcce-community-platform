from marshmallow import Schema, fields, validate

from ..models import PROGRAM_STATUSES


class ProgramCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    slug = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=160))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=5000))
    category = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=60))
    status = fields.String(load_default="Draft", validate=validate.OneOf(PROGRAM_STATUSES))
    start_date = fields.Date(load_default=None, allow_none=True)
    end_date = fields.Date(load_default=None, allow_none=True)
    coordinator_id = fields.Integer(load_default=None, allow_none=True)
    location = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    target_population = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    goals = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=5000))
    image_url = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=500))


class ProgramUpdateSchema(Schema):
    """Partial edit — no load_default on any field, same principle as
    every other *UpdateSchema in this app."""

    name = fields.String(validate=validate.Length(min=1, max=150))
    slug = fields.String(allow_none=True, validate=validate.Length(max=160))
    description = fields.String(allow_none=True, validate=validate.Length(max=5000))
    category = fields.String(allow_none=True, validate=validate.Length(max=60))
    status = fields.String(validate=validate.OneOf(PROGRAM_STATUSES))
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)
    coordinator_id = fields.Integer(allow_none=True)
    location = fields.String(allow_none=True, validate=validate.Length(max=150))
    target_population = fields.String(allow_none=True, validate=validate.Length(max=150))
    goals = fields.String(allow_none=True, validate=validate.Length(max=5000))
    image_url = fields.String(allow_none=True, validate=validate.Length(max=500))
    active = fields.Boolean()
