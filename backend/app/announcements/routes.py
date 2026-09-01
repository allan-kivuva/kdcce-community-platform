from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Announcement, User
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import AnnouncementCreateSchema, AnnouncementUpdateSchema

bp = Blueprint("announcements", __name__, url_prefix="/api/announcements")

create_schema = AnnouncementCreateSchema()
update_schema = AnnouncementUpdateSchema()


@bp.get("")
@jwt_required()
def list_announcements():
    """Default: only announcements currently live AND targeted at the
    caller — never someone else's "Selected" audience, never a still-
    scheduled or already-expired one. `?all=true` is the admin/staff
    management view (every announcement regardless of audience/status);
    it is not available to a volunteer, matching the same
    `include_inactive`-style opt-in used by training/routes.py."""
    role = get_jwt().get("role")
    if role in ("admin", "staff") and request.args.get("all") == "true":
        items = Announcement.query.order_by(Announcement.created_at.desc()).all()
    else:
        user = db.session.get(User, int(get_jwt_identity()))
        items = service.list_active_announcements_for_user(user)
    return jsonify(announcements=[a.to_dict() for a in items]), 200


@bp.post("")
@roles_required("admin", "staff")
def create_announcement():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    announcement = service.create_announcement(int(get_jwt_identity()), data)
    db.session.commit()
    return jsonify(announcement=announcement.to_dict()), 201


@bp.patch("/<int:announcement_id>")
@roles_required("admin", "staff")
def update_announcement(announcement_id):
    announcement = get_or_404(Announcement, announcement_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    service.update_announcement(announcement, data)
    db.session.commit()
    return jsonify(announcement=announcement.to_dict()), 200
