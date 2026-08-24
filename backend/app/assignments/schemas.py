from marshmallow import Schema, fields, validate


class AssignmentMessageCreateSchema(Schema):
    body = fields.String(required=True, validate=validate.Length(min=1, max=4000))
