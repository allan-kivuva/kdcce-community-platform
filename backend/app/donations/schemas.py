from marshmallow import Schema, fields, validate

from ..models import DONATION_FREQUENCIES, DONATION_STATUSES

ALLOWED_CURRENCIES = ("KES",)
ALLOWED_PAYMENT_METHODS = ("M-Pesa", "Card (Stripe)", "PayPal")


class DonationCreateSchema(Schema):
    """Used by the public POST /api/donations endpoint. Deliberately has no
    "status" field — creation status is always server-set, never trusted
    from the client. See the note on Donation.status in models.py."""

    donor_name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    donor_email = fields.Email(required=True)
    donor_phone = fields.String(load_default=None, validate=validate.Length(max=40))
    amount = fields.Decimal(required=True, as_string=False, places=2, validate=validate.Range(min=1))
    currency = fields.String(load_default="KES", validate=validate.OneOf(ALLOWED_CURRENCIES))
    frequency = fields.String(required=True, validate=validate.OneOf(DONATION_FREQUENCIES))
    campaign = fields.String(load_default=None, validate=validate.Length(max=120))
    payment_method = fields.String(load_default=None, validate=validate.OneOf(ALLOWED_PAYMENT_METHODS))
    message = fields.String(load_default=None, validate=validate.Length(max=2000))


class DonationUpdateSchema(Schema):
    """Admin/staff-only edit. Unlike creation, status IS editable here —
    it's an authenticated internal workflow change, not a payment claim."""

    donor_name = fields.String(validate=validate.Length(min=1, max=120))
    donor_email = fields.Email()
    donor_phone = fields.String(allow_none=True, validate=validate.Length(max=40))
    amount = fields.Decimal(as_string=False, places=2, validate=validate.Range(min=1))
    frequency = fields.String(validate=validate.OneOf(DONATION_FREQUENCIES))
    campaign = fields.String(allow_none=True, validate=validate.Length(max=120))
    payment_method = fields.String(allow_none=True, validate=validate.OneOf(ALLOWED_PAYMENT_METHODS))
    status = fields.String(validate=validate.OneOf(DONATION_STATUSES))
