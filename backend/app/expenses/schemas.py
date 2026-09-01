from marshmallow import Schema, fields, validate

from ..models import EXPENSE_CATEGORIES, EXPENSE_STATUSES


class ExpenseMetaSchema(Schema):
    """Multipart form fields alongside an optional receipt file — same
    "form fields arrive as strings" reasoning as
    volunteers/schemas.py:DocumentUploadMetaSchema."""

    amount = fields.Decimal(required=True, as_string=False, places=2, validate=validate.Range(min=0.01))
    category = fields.String(required=True, validate=validate.OneOf(EXPENSE_CATEGORIES))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    program_id = fields.Integer(load_default=None, allow_none=True)
    campaign_id = fields.Integer(load_default=None, allow_none=True)
    expense_date = fields.Date(required=True)
    vendor_name = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))


class ExpenseUpdateSchema(Schema):
    amount = fields.Decimal(as_string=False, places=2, validate=validate.Range(min=0.01))
    category = fields.String(validate=validate.OneOf(EXPENSE_CATEGORIES))
    description = fields.String(allow_none=True, validate=validate.Length(max=2000))
    program_id = fields.Integer(allow_none=True)
    campaign_id = fields.Integer(allow_none=True)
    expense_date = fields.Date()
    vendor_name = fields.String(allow_none=True, validate=validate.Length(max=150))
    status = fields.String(validate=validate.OneOf(EXPENSE_STATUSES))
