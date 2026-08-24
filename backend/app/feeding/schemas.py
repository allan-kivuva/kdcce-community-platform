from marshmallow import Schema, fields, validate

from ..models import MEAL_TYPES


class MealSchema(Schema):
    # No load_default on meal_date: absent on create means "today"
    # (applied in the route), absent on a partial PATCH means "leave it".
    meal_date = fields.Date(allow_none=False)
    meal_type = fields.String(required=True, validate=validate.OneOf(MEAL_TYPES))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class MealAttendanceSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))
