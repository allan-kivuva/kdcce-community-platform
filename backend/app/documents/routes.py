from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Document, VolunteerProfile, utcnow
from ..notifications.service import notify
from ..utils import get_or_404, validation_error_response
from .schemas import DocumentStatusUpdateSchema
from .service import delete_document_file, document_file_path

bp = Blueprint("documents", __name__, url_prefix="/api/documents")

status_schema = DocumentStatusUpdateSchema()

_SNAPSHOT_FIELDS = ("status", "rejection_reason")


def _snapshot(document):
    snapshot = {}
    for field in _SNAPSHOT_FIELDS:
        value = getattr(document, field)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        snapshot[field] = value
    return snapshot


def _can_access(document, role, identity):
    """Generic ownership check, one level of indirection per owner_type —
    today only "volunteer" exists (owner_id is a volunteer_profiles.id,
    matched against the caller's own profile), so a future owner_type
    just adds one more branch here, not a new authorization concept."""
    if role in ("admin", "staff"):
        return True
    if document.owner_type == "volunteer":
        profile = VolunteerProfile.query.filter_by(user_id=identity).first()
        return profile is not None and profile.id == document.owner_id
    return False


@bp.get("/<int:document_id>/file")
@jwt_required()
def get_document_file(document_id):
    document = get_or_404(Document, document_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    if not _can_access(document, role, identity):
        return jsonify(error="Forbidden"), 403
    return send_file(document_file_path(document), mimetype=document.mime_type, download_name=document.original_filename)


@bp.patch("/<int:document_id>/status")
@roles_required("admin", "staff")
def update_document_status(document_id):
    document = get_or_404(Document, document_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = status_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    before = _snapshot(document)
    document.status = data["status"]
    document.rejection_reason = data.get("rejection_reason") if data["status"] == "Rejected" else None
    document.reviewed_by_id = int(get_jwt_identity())
    document.reviewed_at = utcnow()

    after = _snapshot(document)
    if after != before:
        if document.status == "Verified":
            action = "verify"
        elif document.status == "Rejected":
            action = "reject"
        else:
            action = "update"
        log_action(int(get_jwt_identity()), action, "document", document.id, before=before, after=after)

    if document.owner_type == "volunteer":
        profile = db.session.get(VolunteerProfile, document.owner_id)
        if profile is not None:
            if document.status == "Verified":
                notify(
                    profile.user_id, "Document Verified", f'Your "{document.title}" was verified',
                    f"Your {document.document_type} document has been reviewed and verified.",
                    related_resource_type="document", related_resource_id=document.id,
                )
            elif document.status == "Rejected":
                message = f"Your {document.document_type} document was not accepted."
                if document.rejection_reason:
                    message += f" Reason: {document.rejection_reason}"
                notify(
                    profile.user_id, "Document Rejected", f'Your "{document.title}" needs attention',
                    message,
                    related_resource_type="document", related_resource_id=document.id,
                )

    db.session.commit()
    return jsonify(document=document.to_dict()), 200


@bp.delete("/<int:document_id>")
@jwt_required()
def delete_document(document_id):
    """Admin/staff can remove any document. The owner can remove their own
    only while it's still Pending — once reviewed, it's part of the
    review record and no longer the uploader's to unilaterally delete."""
    document = get_or_404(Document, document_id)
    role = get_jwt().get("role")
    identity = int(get_jwt_identity())
    if role not in ("admin", "staff"):
        if not _can_access(document, role, identity) or document.status != "Pending":
            return jsonify(error="Forbidden"), 403

    delete_document_file(document)
    db.session.delete(document)
    db.session.commit()
    return "", 204
