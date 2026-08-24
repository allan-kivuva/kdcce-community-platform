from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..extensions import db
from ..models import Notification, utcnow
from ..utils import validation_error_response
from .schemas import NotificationUpdateSchema

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")

update_schema = NotificationUpdateSchema()


def _own_notification_or_none(notification_id):
    """Scoped to the caller's own id at the query level — a mismatch
    returns None (the route then 404s) rather than finding the row and
    checking ownership afterward. That's deliberate: it means a request
    for someone else's notification looks identical to a request for one
    that doesn't exist at all, which is the point — no endpoint here ever
    confirms another user's notification even exists."""
    return Notification.query.filter_by(id=notification_id, recipient_id=int(get_jwt_identity())).first()


@bp.get("")
@jwt_required()
def list_notifications():
    query = Notification.query.filter_by(recipient_id=int(get_jwt_identity()))
    if request.args.get("unread_only") == "true":
        query = query.filter_by(is_read=False)
    notification_type = request.args.get("notification_type")
    if notification_type:
        query = query.filter_by(notification_type=notification_type)

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    query = query.order_by(Notification.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        notifications=[n.to_dict() for n in items],
        pagination={"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page if per_page else 0},
    ), 200


@bp.get("/unread-count")
@jwt_required()
def unread_count():
    count = Notification.query.filter_by(recipient_id=int(get_jwt_identity()), is_read=False).count()
    return jsonify(unread_count=count), 200


@bp.patch("/<int:notification_id>")
@jwt_required()
def update_notification(notification_id):
    notification = _own_notification_or_none(notification_id)
    if notification is None:
        return jsonify(error="Notification not found"), 404

    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    notification.is_read = data["is_read"]
    notification.read_at = utcnow() if data["is_read"] else None
    db.session.commit()
    return jsonify(notification=notification.to_dict()), 200


@bp.post("/mark-all-read")
@jwt_required()
def mark_all_read():
    now = utcnow()
    updated = Notification.query.filter_by(recipient_id=int(get_jwt_identity()), is_read=False).update(
        {"is_read": True, "read_at": now}, synchronize_session=False
    )
    db.session.commit()
    return jsonify(updated=updated), 200


@bp.delete("/<int:notification_id>")
@jwt_required()
def delete_notification(notification_id):
    notification = _own_notification_or_none(notification_id)
    if notification is None:
        return jsonify(error="Notification not found"), 404

    db.session.delete(notification)
    db.session.commit()
    return "", 204
