from marshmallow import Schema, fields, validate


class AssignmentMessageCreateSchema(Schema):
    body = fields.String(required=True, validate=validate.Length(min=1, max=4000))


class AssignmentReviewCreateSchema(Schema):
    rating = fields.Integer(required=True, validate=validate.Range(min=1, max=5))
    comment = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
