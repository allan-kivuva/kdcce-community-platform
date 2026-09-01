from marshmallow import Schema, fields, validate

from ..models import INVENTORY_CATEGORIES, STOCK_MOVEMENT_TYPES


class InventoryItemSchema(Schema):
    """current_stock is deliberately not a field here — it can only ever
    change via a StockMovement (see routes.py's create_movement)."""

    name = fields.String(required=True, validate=validate.Length(min=1, max=150))
    # No load_default on category/minimum_stock: a meaningful non-null
    # default only applies at creation (handled in the route) — applying
    # it on every partial PATCH that omits the field would silently reset it.
    category = fields.String(allow_none=False, validate=validate.OneOf(INVENTORY_CATEGORIES))
    unit = fields.String(required=True, validate=validate.Length(min=1, max=30))
    minimum_stock = fields.Decimal(allow_none=False, as_string=False, places=2, validate=validate.Range(min=0))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class StockMovementSchema(Schema):
    movement_type = fields.String(required=True, validate=validate.OneOf(STOCK_MOVEMENT_TYPES))
    quantity = fields.Decimal(required=True, as_string=False, places=2, validate=validate.Range(min=0.01))
    reason = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))
    expiry_date = fields.Date(load_default=None, allow_none=True)
    donation_id = fields.Integer(load_default=None, allow_none=True)


class DistributionCreateSchema(Schema):
    """A distribution is always a stock-OUT to a named recipient — there
    is no movement_type field here, unlike StockMovementSchema, since
    it's never anything else."""

    elderly_member_id = fields.Integer(required=True)
    program_id = fields.Integer(load_default=None, allow_none=True)
    quantity = fields.Decimal(required=True, as_string=False, places=2, validate=validate.Range(min=0.01))
    reason = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=200))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
