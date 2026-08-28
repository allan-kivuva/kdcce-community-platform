from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from ..models import DONATION_FREQUENCIES, DONATION_STATUSES, DONATION_TYPES

ALLOWED_CURRENCIES = ("KES",)
ALLOWED_PAYMENT_METHODS = ("M-Pesa", "Card (Stripe)", "PayPal")


class DonationCreateSchema(Schema):
    """Used by the public POST /api/donations endpoint — Cash only, and
    unchanged since before donation_type existed. Deliberately has no
    "status" or "donation_type" field — both are always server-set, never
    trusted from the client. See the note on Donation.status in models.py.
    In-kind (Food/Equipment) donations are staff-logged only, via
    AdminDonationCreateSchema below — there's no public self-service path
    for "I dropped off a bag of rice.\""""

    donor_name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    donor_email = fields.Email(required=True)
    donor_phone = fields.String(load_default=None, validate=validate.Length(max=40))
    amount = fields.Decimal(required=True, as_string=False, places=2, validate=validate.Range(min=1))
    currency = fields.String(load_default="KES", validate=validate.OneOf(ALLOWED_CURRENCIES))
    frequency = fields.String(required=True, validate=validate.OneOf(DONATION_FREQUENCIES))
    campaign = fields.String(load_default=None, validate=validate.Length(max=120))
    payment_method = fields.String(load_default=None, validate=validate.OneOf(ALLOWED_PAYMENT_METHODS))
    message = fields.String(load_default=None, validate=validate.Length(max=2000))


class AdminDonationCreateSchema(Schema):
    """Staff/admin logging a donation received in person — any type,
    including a cash gift handed over rather than paid through the public
    form. Field requirements differ by donation_type; see
    _check_type_specific_fields."""

    donation_type = fields.String(required=True, validate=validate.OneOf(DONATION_TYPES))
    donor_name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    donor_email = fields.Email(load_default=None, allow_none=True)
    donor_phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=40))
    amount = fields.Decimal(load_default=None, allow_none=True, as_string=False, places=2, validate=validate.Range(min=0.01))
    currency = fields.String(load_default="KES", validate=validate.OneOf(ALLOWED_CURRENCIES))
    payment_method = fields.String(load_default=None, allow_none=True, validate=validate.OneOf(ALLOWED_PAYMENT_METHODS))
    campaign = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=120))
    item_description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))
    quantity = fields.Decimal(load_default=None, allow_none=True, as_string=False, places=2, validate=validate.Range(min=0.01))
    unit = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=30))
    message = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))

    @validates_schema
    def _check_type_specific_fields(self, data, **kwargs):
        errors = {}
        if data["donation_type"] == "Cash":
            if data.get("amount") is None:
                errors.setdefault("amount", []).append("Required for a cash donation.")
        else:
            if not data.get("item_description"):
                errors.setdefault("item_description", []).append("Required for an in-kind donation.")
            if data.get("quantity") is None:
                errors.setdefault("quantity", []).append("Required for an in-kind donation.")
            if not data.get("unit"):
                errors.setdefault("unit", []).append("Required for an in-kind donation.")
        if errors:
            raise ValidationError(errors)


class DonationUpdateSchema(Schema):
    """Admin/staff-only edit. Unlike creation, status IS editable here —
    it's an authenticated internal workflow change, not a payment claim.
    No load_default on any field (including the new ones): omitted on a
    partial PATCH must mean "leave it alone," never "reset it.\""""

    donation_type = fields.String(validate=validate.OneOf(DONATION_TYPES))
    donor_name = fields.String(validate=validate.Length(min=1, max=120))
    donor_email = fields.Email(allow_none=True)
    donor_phone = fields.String(allow_none=True, validate=validate.Length(max=40))
    amount = fields.Decimal(allow_none=True, as_string=False, places=2, validate=validate.Range(min=0.01))
    frequency = fields.String(validate=validate.OneOf(DONATION_FREQUENCIES))
    campaign = fields.String(allow_none=True, validate=validate.Length(max=120))
    payment_method = fields.String(allow_none=True, validate=validate.OneOf(ALLOWED_PAYMENT_METHODS))
    item_description = fields.String(allow_none=True, validate=validate.Length(max=1000))
    quantity = fields.Decimal(allow_none=True, as_string=False, places=2, validate=validate.Range(min=0.01))
    unit = fields.String(allow_none=True, validate=validate.Length(max=30))
    status = fields.String(validate=validate.OneOf(DONATION_STATUSES))
