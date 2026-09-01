from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class BudgetCreateSchema(Schema):
    program_id = fields.Integer(required=True)
    period_start = fields.Date(load_default=None, allow_none=True)
    period_end = fields.Date(load_default=None, allow_none=True)
    allocated_amount = fields.Decimal(required=True, as_string=False, places=2, validate=validate.Range(min=0))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))

    @validates_schema
    def validate_period(self, data, **kwargs):
        if data.get("period_start") and data.get("period_end") and data["period_end"] < data["period_start"]:
            raise ValidationError({"period_end": ["Must not be before period_start"]})


class BudgetUpdateSchema(Schema):
    period_start = fields.Date(allow_none=True)
    period_end = fields.Date(allow_none=True)
    allocated_amount = fields.Decimal(as_string=False, places=2, validate=validate.Range(min=0))
    notes = fields.String(allow_none=True, validate=validate.Length(max=2000))
