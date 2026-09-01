from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Broadcast
from ..utils import validation_error_response
from . import service
from .schemas import BroadcastCreateSchema

bp = Blueprint("broadcasts", __name__, url_prefix="/api/broadcasts")

create_schema = BroadcastCreateSchema()


@bp.get("")
@roles_required("admin", "staff")
def list_broadcasts():
    items = Broadcast.query.order_by(Broadcast.created_at.desc()).limit(50).all()
    return jsonify(broadcasts=[b.to_dict() for b in items]), 200


@bp.post("")
@roles_required("admin", "staff")
def create_broadcast():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    broadcast, created = service.create_broadcast(
        int(get_jwt_identity()), data["audience_type"], data["title"], data["message"],
        selected_user_ids=data.get("selected_user_ids"), client_token=data.get("client_token"),
    )
    db.session.commit()
    return jsonify(broadcast=broadcast.to_dict()), 201 if created else 200
