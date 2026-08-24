from marshmallow import Schema, fields, validate

from ..models import ADMINISTRATION_STATUSES, MEDICATION_STATUSES


class MedicationSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    dosage = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    instructions = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    schedule = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    # start_date/status: no load_default. A brand-new default only makes
    # sense at creation (handled in the route) — applying it on every
    # partial PATCH that omits the field would silently reset it.
    start_date = fields.Date(allow_none=False)
    end_date = fields.Date(load_default=None, allow_none=True)
    status = fields.String(allow_none=False, validate=validate.OneOf(MEDICATION_STATUSES))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class MedicationAdministrationSchema(Schema):
    status = fields.String(load_default="Given", validate=validate.OneOf(ADMINISTRATION_STATUSES))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
