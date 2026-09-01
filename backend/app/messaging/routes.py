from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..family.service import authorized_access
from ..models import DirectMessage, User, utcnow
from ..notifications.service import notify
from ..utils import validation_error_response
from . import service
from .schemas import ConversationCreateSchema, DirectMessageCreateSchema

bp = Blueprint("messaging", __name__, url_prefix="/api/messages")

conversation_create_schema = ConversationCreateSchema()
message_create_schema = DirectMessageCreateSchema()


def _identity():
    return int(get_jwt_identity()), get_jwt().get("role")


@bp.get("/recipients")
@jwt_required()
def list_recipients():
    identity, role = _identity()
    people = service.list_recipients(role, identity)
    return jsonify(recipients=[{"id": u.id, "name": u.name, "role": u.role} for u in people]), 200


@bp.get("/templates")
@roles_required("admin", "staff")
def list_templates():
    return jsonify(templates=service.MESSAGE_TEMPLATES), 200


@bp.get("/conversations")
@jwt_required()
def list_conversations():
    identity, _ = _identity()
    return jsonify(conversations=service.list_conversations_for_user(identity)), 200


@bp.post("/conversations")
@jwt_required()
def create_conversation():
    identity, role = _identity()
    payload = request.get_json(silent=True) or {}
    try:
        data = conversation_create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    recipient = db.session.get(User, data["recipient_id"])
    if not service.can_message(role, identity, recipient):
        return jsonify(error="Validation failed", details={"recipient_id": ["Not a valid recipient"]}), 400

    elderly_member_id = None
    if role == "family" and data.get("elderly_member_id") is not None:
        if authorized_access(identity, data["elderly_member_id"]) is None:
            return jsonify(error="Validation failed", details={"elderly_member_id": ["Not authorized for this member"]}), 400
        elderly_member_id = data["elderly_member_id"]

    conversation = service.get_or_create_conversation(identity, recipient.id, elderly_member_id=elderly_member_id)
    message = service.send_direct_message(conversation, identity, data["body"])
    notify(
        recipient.id, "Direct Message", f"New message from {message.sender.name}", data["body"][:200],
        related_resource_type="conversation", related_resource_id=conversation.id,
    )
    db.session.commit()
    return jsonify(conversation=_conversation_detail(conversation, identity)), 201


def _conversation_detail(conversation, identity):
    other = conversation.other_user(identity)
    messages = DirectMessage.query.filter_by(conversation_id=conversation.id).order_by(DirectMessage.created_at.asc()).all()
    return {
        "id": conversation.id,
        "other_user": {"id": other.id, "name": other.name, "role": other.role},
        "messages": [m.to_dict() for m in messages],
    }


@bp.get("/conversations/<int:conversation_id>")
@jwt_required()
def get_conversation(conversation_id):
    identity, _ = _identity()
    conversation = service.participant_conversation_or_none(conversation_id, identity)
    if conversation is None:
        return jsonify(error="Conversation not found"), 404
    return jsonify(conversation=_conversation_detail(conversation, identity)), 200


@bp.post("/conversations/<int:conversation_id>/messages")
@jwt_required()
def send_message(conversation_id):
    identity, _ = _identity()
    conversation = service.participant_conversation_or_none(conversation_id, identity)
    if conversation is None:
        return jsonify(error="Conversation not found"), 404

    payload = request.get_json(silent=True) or {}
    try:
        data = message_create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    message = service.send_direct_message(conversation, identity, data["body"])
    recipient_id = conversation.other_user(identity).id
    notify(
        recipient_id, "Direct Message", f"New message from {message.sender.name}", data["body"][:200],
        related_resource_type="conversation", related_resource_id=conversation.id,
    )
    db.session.commit()
    return jsonify(message=message.to_dict()), 201


@bp.patch("/conversations/<int:conversation_id>/read")
@jwt_required()
def mark_conversation_read(conversation_id):
    identity, _ = _identity()
    conversation = service.participant_conversation_or_none(conversation_id, identity)
    if conversation is None:
        return jsonify(error="Conversation not found"), 404

    conversation.set_read_at_for(identity, utcnow())
    db.session.commit()
    return jsonify(conversation=_conversation_detail(conversation, identity)), 200


@bp.get("/unread-count")
@jwt_required()
def unread_count():
    identity, _ = _identity()
    return jsonify(unread_count=service.unread_message_count(identity)), 200


@bp.get("/unresolved")
@roles_required("admin", "staff")
def unresolved():
    return jsonify(unresolved=service.list_unresolved_conversations()), 200


@bp.get("/assignment-conversations")
@roles_required("admin", "staff")
def assignment_conversations():
    return jsonify(conversations=service.list_assignment_conversations()), 200
