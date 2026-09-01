from marshmallow import Schema, fields, validate

MAX_QUESTION_LENGTH = 300


class AIQuerySchema(Schema):
    question = fields.String(required=True, validate=validate.Length(min=1, max=MAX_QUESTION_LENGTH))


class TimelineSummarySchema(Schema):
    days = fields.Integer(load_default=30, validate=validate.OneOf((7, 30, 90, 365)))
    since = fields.Date(load_default=None, allow_none=True)
    until = fields.Date(load_default=None, allow_none=True)
