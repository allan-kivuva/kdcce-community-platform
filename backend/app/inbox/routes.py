from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db, limiter
from ..models import InboxMessage
from ..utils import get_or_404, validation_error_response
from .schemas import InboxMessageCreateSchema, InboxMessageUpdateSchema

# Public submission endpoint and staff-facing management endpoints live at
# different URL prefixes — same two-blueprint pattern as donations/routes.py
# (bp vs admin_bp) — so the public path never shares a prefix with anything
# requiring auth.
bp = Blueprint("inbox", __name__, url_prefix="/api/inbox")
admin_bp = Blueprint("admin_inbox", __name__, url_prefix="/api/admin/inbox")

create_schema = InboxMessageCreateSchema()
update_schema = InboxMessageUpdateSchema()


@bp.post("")
@limiter.limit("10 per minute")
def create_message():
    """Public, unauthenticated: the site's contact form. Rate-limited like
    auth's public endpoints — a text form is a typical spam-bot target."""
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    inbox_message = InboxMessage(
        name=data["name"].strip(),
        email=data["email"].lower(),
        subject=data["subject"].strip(),
        message=data["message"],
    )
    db.session.add(inbox_message)
    db.session.commit()
    return jsonify(message=inbox_message.to_dict()), 201


@admin_bp.get("")
@roles_required("admin", "staff")
def list_messages():
    query = InboxMessage.query
    if request.args.get("unread_only") == "true":
        query = query.filter_by(is_read=False)

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    query = query.order_by(InboxMessage.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        messages=[m.to_dict() for m in items],
        pagination={"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page if per_page else 0},
    ), 200


@admin_bp.patch("/<int:message_id>")
@roles_required("admin", "staff")
def update_message(message_id):
    inbox_message = get_or_404(InboxMessage, message_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    inbox_message.is_read = data["is_read"]
    db.session.commit()
    return jsonify(message=inbox_message.to_dict()), 200


@admin_bp.delete("/<int:message_id>")
@roles_required("admin", "staff")
def delete_message(message_id):
    inbox_message = get_or_404(InboxMessage, message_id)
    db.session.delete(inbox_message)
    db.session.commit()
    return "", 204
