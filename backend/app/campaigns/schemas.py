from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from ..models import CAMPAIGN_STATUSES


class CampaignCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    slug = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=160))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=5000))
    goal_amount = fields.Decimal(required=True, as_string=False, places=2, validate=validate.Range(min=0.01))
    program_id = fields.Integer(load_default=None, allow_none=True)
    start_date = fields.Date(load_default=None, allow_none=True)
    end_date = fields.Date(load_default=None, allow_none=True)
    status = fields.String(load_default="Draft", validate=validate.OneOf(CAMPAIGN_STATUSES))
    public_visible = fields.Boolean(load_default=False)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data.get("start_date") and data.get("end_date") and data["end_date"] < data["start_date"]:
            raise ValidationError({"end_date": ["Must not be before start_date"]})


class CampaignUpdateSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=150))
    slug = fields.String(allow_none=True, validate=validate.Length(max=160))
    description = fields.String(allow_none=True, validate=validate.Length(max=5000))
    goal_amount = fields.Decimal(as_string=False, places=2, validate=validate.Range(min=0.01))
    program_id = fields.Integer(allow_none=True)
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)
    status = fields.String(validate=validate.OneOf(CAMPAIGN_STATUSES))
    public_visible = fields.Boolean()
