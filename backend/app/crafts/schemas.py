from marshmallow import Schema, fields, validate

from ..models import CRAFT_STATUSES

ALLOWED_CATEGORIES = ("Beadwork", "Knitting", "Other")


class CraftSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    category = fields.String(required=True, validate=validate.OneOf(ALLOWED_CATEGORIES))
    maker = fields.String(required=True, validate=validate.Length(min=1, max=120))
    price = fields.Decimal(required=True, as_string=False, places=2, validate=validate.Range(min=1))
    status = fields.String(load_default="Available", validate=validate.OneOf(CRAFT_STATUSES))
    image = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=500))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
