from marshmallow import Schema, fields, validate


class CheckInSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class CheckOutSchema(Schema):
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
