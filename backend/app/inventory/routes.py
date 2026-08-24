from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Donation, InventoryItem, StockMovement
from ..utils import get_or_404, validation_error_response
from .schemas import InventoryItemSchema, StockMovementSchema

bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")

item_schema = InventoryItemSchema()
movement_schema = StockMovementSchema()


@bp.post("")
@roles_required("admin", "staff")
def create_item():
    payload = request.get_json(silent=True) or {}
    try:
        data = item_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    if InventoryItem.query.filter_by(name=data["name"]).first():
        return jsonify(error="An inventory item with that name already exists"), 409

    data.setdefault("category", "Other")
    data.setdefault("minimum_stock", 0)
    # current_stock is never client-settable, even on create — an initial
    # quantity is a stock-in movement (POST .../movements), not a field
    # here. That keeps the ledger the single source of truth from day one.
    item = InventoryItem(**data, current_stock=0)
    db.session.add(item)
    db.session.commit()
    return jsonify(item=item.to_dict()), 201


@bp.get("")
@roles_required("admin", "staff")
def list_items():
    query = InventoryItem.query
    category = request.args.get("category")
    if category:
        query = query.filter(InventoryItem.category == category)

    items = [i.to_dict() for i in query.order_by(InventoryItem.name.asc()).all()]
    if request.args.get("low_stock") == "true":
        items = [i for i in items if i["low_stock"]]
    return jsonify(items=items), 200


@bp.get("/<int:item_id>")
@roles_required("admin", "staff")
def get_item(item_id):
    item = get_or_404(InventoryItem, item_id)
    return jsonify(item=item.to_dict()), 200


@bp.patch("/<int:item_id>")
@roles_required("admin", "staff")
def update_item(item_id):
    item = get_or_404(InventoryItem, item_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = item_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "name" in data and data["name"] != item.name and InventoryItem.query.filter_by(name=data["name"]).first():
        return jsonify(error="An inventory item with that name already exists"), 409

    for field, value in data.items():
        setattr(item, field, value)
    db.session.commit()
    return jsonify(item=item.to_dict()), 200


@bp.delete("/<int:item_id>")
@roles_required("admin")
def delete_item(item_id):
    item = get_or_404(InventoryItem, item_id)
    db.session.delete(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="This item has stock movement history and cannot be deleted."), 409
    return "", 204


# ---------- Stock movements (append-only — no edit/delete) ----------

@bp.post("/<int:item_id>/movements")
@roles_required("admin", "staff")
def create_movement(item_id):
    item = get_or_404(InventoryItem, item_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = movement_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    if data.get("donation_id") is not None and db.session.get(Donation, data["donation_id"]) is None:
        return jsonify(error="Validation failed", details={"donation_id": ["Donation not found"]}), 400

    if data["movement_type"] == "Out" and data["quantity"] > item.current_stock:
        return jsonify(error=f"Insufficient stock: {item.current_stock} {item.unit} available, {data['quantity']} requested"), 400

    movement = StockMovement(
        item_id=item.id,
        movement_type=data["movement_type"],
        quantity=data["quantity"],
        reason=data.get("reason"),
        expiry_date=data.get("expiry_date") if data["movement_type"] == "In" else None,
        donation_id=data.get("donation_id"),
        recorded_by_id=int(get_jwt_identity()),
    )
    item.current_stock = item.current_stock + data["quantity"] if data["movement_type"] == "In" else item.current_stock - data["quantity"]

    db.session.add(movement)
    try:
        # Movement row + balance update committed together — if either
        # fails, both roll back, so current_stock can never end up out of
        # sync with the ledger it's derived from.
        db.session.commit()
    except IntegrityError:
        # Backstop for the DB-level CHECK (current_stock >= 0) in case a
        # race slipped past the check above — should not happen under this
        # app's synchronous request handling, but never surface it as 500.
        db.session.rollback()
        return jsonify(error="This movement would take stock below zero."), 400

    return jsonify(movement=movement.to_dict(), item=item.to_dict()), 201


@bp.get("/<int:item_id>/movements")
@roles_required("admin", "staff")
def list_movements(item_id):
    get_or_404(InventoryItem, item_id)
    movements = StockMovement.query.filter_by(item_id=item_id).order_by(StockMovement.created_at.desc()).all()
    return jsonify(movements=[m.to_dict() for m in movements]), 200
