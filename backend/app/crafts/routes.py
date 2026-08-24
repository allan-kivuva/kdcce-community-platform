from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Craft
from ..utils import get_or_404, validation_error_response
from .schemas import CraftSchema

bp = Blueprint("crafts", __name__)

schema = CraftSchema()


@bp.get("/api/crafts")
def list_crafts():
    crafts = Craft.query.order_by(Craft.created_at.desc()).all()
    return jsonify(crafts=[c.to_dict() for c in crafts]), 200


@bp.post("/api/admin/crafts")
@roles_required("admin", "staff")
def create_craft():
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    craft = Craft(**data)
    db.session.add(craft)
    db.session.commit()
    return jsonify(craft=craft.to_dict()), 201


@bp.patch("/api/admin/crafts/<int:craft_id>")
@roles_required("admin", "staff")
def update_craft(craft_id):
    craft = get_or_404(Craft, craft_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    for field, value in data.items():
        setattr(craft, field, value)
    db.session.commit()
    return jsonify(craft=craft.to_dict()), 200


@bp.delete("/api/admin/crafts/<int:craft_id>")
@roles_required("admin", "staff")
def delete_craft(craft_id):
    craft = get_or_404(Craft, craft_id)
    db.session.delete(craft)
    db.session.commit()
    return "", 204
