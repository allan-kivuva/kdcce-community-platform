from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Distribution, Donation, ElderlyMember, InventoryItem, Program, StockMovement
from ..utils import get_or_404, validation_error_response
from . import service as inventory_service
from .schemas import DistributionCreateSchema, InventoryItemSchema, StockMovementSchema

bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")

item_schema = InventoryItemSchema()
movement_schema = StockMovementSchema()
distribution_schema = DistributionCreateSchema()


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

    try:
        movement = inventory_service.apply_movement(
            item, data["movement_type"], data["quantity"], int(get_jwt_identity()),
            reason=data.get("reason"), expiry_date=data.get("expiry_date"), donation_id=data.get("donation_id"),
        )
    except inventory_service.InsufficientStockError as err:
        return jsonify(error=f"Insufficient stock: {err.available} {item.unit} available, {err.requested} requested"), 400

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


# ---------- Distributions (a stock-out to a named recipient) ----------

@bp.post("/<int:item_id>/distributions")
@roles_required("admin", "staff")
def create_distribution(item_id):
    """Creates the underlying StockMovement("Out") via the same
    apply_movement() the plain movement endpoint uses, plus a
    Distribution row linking it to a specific elderly member (and,
    optionally, a program) — see the Distribution model docstring for
    why this is additive on top of the ledger rather than a new one."""
    item = get_or_404(InventoryItem, item_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = distribution_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    get_or_404(ElderlyMember, data["elderly_member_id"])
    if data.get("program_id") is not None and db.session.get(Program, data["program_id"]) is None:
        return jsonify(error="Validation failed", details={"program_id": ["Program not found"]}), 400

    try:
        movement = inventory_service.apply_movement(
            item, "Out", data["quantity"], int(get_jwt_identity()), reason=data.get("reason"),
        )
    except inventory_service.InsufficientStockError as err:
        return jsonify(error=f"Insufficient stock: {err.available} {item.unit} available, {err.requested} requested"), 400

    db.session.flush()  # assigns movement.id
    distribution = Distribution(
        item_id=item.id, elderly_member_id=data["elderly_member_id"], program_id=data.get("program_id"),
        movement_id=movement.id, quantity=data["quantity"], recorded_by_id=int(get_jwt_identity()),
        reason=data.get("reason"), notes=data.get("notes"),
    )
    db.session.add(distribution)
    db.session.flush()
    log_action(
        int(get_jwt_identity()), "create", "distribution", distribution.id,
        after={"item_id": item.id, "elderly_member_id": distribution.elderly_member_id, "quantity": float(distribution.quantity)},
    )

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="This distribution would take stock below zero."), 400

    return jsonify(distribution=distribution.to_dict(), item=item.to_dict()), 201


@bp.get("/distributions")
@roles_required("admin", "staff")
def list_distributions():
    query = Distribution.query
    item_id = request.args.get("item_id", type=int)
    if item_id is not None:
        query = query.filter_by(item_id=item_id)
    elderly_member_id = request.args.get("elderly_member_id", type=int)
    if elderly_member_id is not None:
        query = query.filter_by(elderly_member_id=elderly_member_id)
    program_id = request.args.get("program_id", type=int)
    if program_id is not None:
        query = query.filter_by(program_id=program_id)

    rows = query.order_by(Distribution.distributed_at.desc()).limit(200).all()
    return jsonify(distributions=[d.to_dict() for d in rows]), 200
