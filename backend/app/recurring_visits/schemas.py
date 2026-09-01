from datetime import time

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from ..models import HOME_VISIT_PRIORITIES, RECURRING_FREQUENCIES, RECURRING_SERIES_STATUSES


class RecurringVisitSeriesCreateSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    assigned_to_id = fields.Integer(load_default=None, allow_none=True)
    reason = fields.String(required=True, validate=validate.Length(min=1, max=2000))
    priority = fields.String(allow_none=False, validate=validate.OneOf(HOME_VISIT_PRIORITIES))
    frequency = fields.String(required=True, validate=validate.OneOf(RECURRING_FREQUENCIES))
    start_date = fields.Date(required=True)
    scheduled_time = fields.Time(load_default=time(9, 0))
    end_date = fields.Date(load_default=None, allow_none=True)
    occurrence_count = fields.Integer(load_default=None, allow_none=True, validate=validate.Range(min=1))

    @validates_schema
    def validate_bounds(self, data, **kwargs):
        if data.get("end_date") and data["end_date"] < data["start_date"]:
            raise ValidationError({"end_date": ["Must not be before start_date"]})


class RecurringVisitSeriesUpdateSchema(Schema):
    """Editable after creation — deliberately NOT frequency/start_date:
    changing the pattern anchor after occurrences already exist would
    desync already-generated dates from the new pattern. To change the
    recurrence itself, cancel this series and create a new one."""

    assigned_to_id = fields.Integer(allow_none=True)
    reason = fields.String(validate=validate.Length(min=1, max=2000))
    priority = fields.String(allow_none=False, validate=validate.OneOf(HOME_VISIT_PRIORITIES))
    end_date = fields.Date(allow_none=True)
    occurrence_count = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    status = fields.String(allow_none=False, validate=validate.OneOf(RECURRING_SERIES_STATUSES))
