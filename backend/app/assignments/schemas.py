from marshmallow import Schema, fields, validate


class AssignmentMessageCreateSchema(Schema):
    body = fields.String(required=True, validate=validate.Length(min=1, max=4000))


class AssignmentReviewCreateSchema(Schema):
    rating = fields.Integer(required=True, validate=validate.Range(min=1, max=5))
    comment = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class ChecklistItemUpdateSchema(Schema):
    item_key = fields.String(required=True, validate=validate.Length(min=1, max=40))
    checked = fields.Boolean(required=True)
