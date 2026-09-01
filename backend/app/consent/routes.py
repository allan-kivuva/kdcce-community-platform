from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Consent, Document, ElderlyMember
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import ConsentCreateSchema

bp = Blueprint("consent", __name__, url_prefix="/api/consents")

create_schema = ConsentCreateSchema()


@bp.get("")
@roles_required("admin", "staff")
def list_consents():
    """By default, returns only the current (latest) row per (member,
    type) — the live status. Pass ?history=true to see every decision
    ever recorded for a member (an append-only audit trail in its own
    right, useful for a compliance review)."""
    elderly_member_id = request.args.get("elderly_member_id", type=int)
    consent_type = request.args.get("consent_type")
    show_history = request.args.get("history", "false").lower() == "true"

    query = Consent.query
    if elderly_member_id is not None:
        query = query.filter_by(elderly_member_id=elderly_member_id)
    if consent_type:
        query = query.filter_by(consent_type=consent_type)
    rows = query.order_by(Consent.created_at.desc()).all()

    if show_history:
        return jsonify(consents=[c.to_dict() for c in rows]), 200

    latest_by_key = {}
    for row in rows:  # already newest-first, so the first hit per key wins
        key = (row.elderly_member_id, row.consent_type)
        latest_by_key.setdefault(key, row)
    return jsonify(consents=[c.to_dict() for c in latest_by_key.values()]), 200


@bp.post("")
@roles_required("admin", "staff")
def create_consent():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    get_or_404(ElderlyMember, data["elderly_member_id"])
    if data.get("document_id") is not None and db.session.get(Document, data["document_id"]) is None:
        return jsonify(error="Validation failed", details={"document_id": ["Document not found"]}), 400

    consent = service.record_consent(
        data["elderly_member_id"], data["consent_type"], data["status"], int(get_jwt_identity()),
        notes=data.get("notes"), document_id=data.get("document_id"),
    )
    db.session.flush()
    log_action(
        int(get_jwt_identity()), "record", "consent", consent.id,
        after={"elderly_member_id": consent.elderly_member_id, "consent_type": consent.consent_type, "status": consent.status},
    )
    db.session.commit()
    return jsonify(consent=consent.to_dict()), 201
