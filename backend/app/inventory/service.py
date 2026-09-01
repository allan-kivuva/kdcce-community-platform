from ..extensions import db
from ..models import StockMovement, User
from ..notifications.service import notify


class InsufficientStockError(Exception):
    def __init__(self, available, requested):
        self.available = available
        self.requested = requested


def apply_movement(item, movement_type, quantity, recorded_by_id, reason=None, expiry_date=None, donation_id=None):
    """The one place that mutates InventoryItem.current_stock and fires
    the low-stock alert — used by both the plain stock-movement route
    and Distribution creation (see routes.py:create_distribution), so
    the two can never drift into different balance/alert behavior.
    Does not commit; the caller commits (and, for a Distribution,
    creates its own linking row) in the same transaction. Raises
    InsufficientStockError rather than returning a response — callers
    translate that into their own 400."""
    if movement_type == "Out" and quantity > item.current_stock:
        raise InsufficientStockError(item.current_stock, quantity)

    was_low_stock = item.current_stock <= item.minimum_stock

    movement = StockMovement(
        item_id=item.id, movement_type=movement_type, quantity=quantity, reason=reason,
        expiry_date=expiry_date if movement_type == "In" else None,
        donation_id=donation_id, recorded_by_id=recorded_by_id,
    )
    item.current_stock = item.current_stock + quantity if movement_type == "In" else item.current_stock - quantity

    if not was_low_stock and item.current_stock <= item.minimum_stock:
        for staff_member in User.query.filter(User.role.in_(("admin", "staff"))).all():
            notify(
                staff_member.id, "Low Inventory Alert", f"Low stock: {item.name}",
                f"{item.name} is at {item.current_stock} {item.unit}, at or below the minimum of {item.minimum_stock} {item.unit}.",
                related_resource_type="inventory_item", related_resource_id=item.id,
            )

    db.session.add(movement)
    return movement
