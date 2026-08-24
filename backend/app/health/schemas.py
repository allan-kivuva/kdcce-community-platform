from marshmallow import Schema, fields, validate

from ..models import WELLBEING_LEVELS


class HealthRecordSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    # No load_default: omitted on a partial (PATCH) load means "leave it
    # alone", not "set to None" — recorded_at is NOT NULL in the DB.
    recorded_at = fields.DateTime(allow_none=True)
    blood_pressure_systolic = fields.Integer(load_default=None, allow_none=True, validate=validate.Range(min=1, max=400))
    blood_pressure_diastolic = fields.Integer(load_default=None, allow_none=True, validate=validate.Range(min=1, max=300))
    temperature_celsius = fields.Decimal(load_default=None, allow_none=True, as_string=False, places=1, validate=validate.Range(min=20, max=45))
    pulse_bpm = fields.Integer(load_default=None, allow_none=True, validate=validate.Range(min=1, max=300))
    weight_kg = fields.Decimal(load_default=None, allow_none=True, as_string=False, places=1, validate=validate.Range(min=1, max=400))
    wellbeing = fields.String(load_default=None, allow_none=True, validate=validate.OneOf(WELLBEING_LEVELS))
    mood = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=60))
    physical_activity = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))
    observations = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=4000))
    # No load_default: defaults to False only at creation (in the route),
    # not on every partial edit that happens to omit it.
    follow_up_required = fields.Boolean()
    follow_up_notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
