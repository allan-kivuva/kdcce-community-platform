from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..documents.service import document_file_path, delete_document_file
from ..extensions import db
from ..models import Document
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import ResourceUploadMetaSchema

bp = Blueprint("resources", __name__, url_prefix="/api/resources")

upload_meta_schema = ResourceUploadMetaSchema()


@bp.get("")
@jwt_required()
def list_resources():
    role = get_jwt().get("role")
    program_id = request.args.get("program_id", type=int)
    activity_id = request.args.get("activity_id", type=int)
    category = request.args.get("category")
    resources = service.list_resources(role, program_id=program_id, activity_id=activity_id, category=category)
    return jsonify(resources=[r.to_dict() for r in resources]), 200


@bp.post("")
@roles_required("admin", "staff")
def upload_resource():
    try:
        meta = upload_meta_schema.load(request.form.to_dict())
    except ValidationError as err:
        return validation_error_response(err)

    identity = int(get_jwt_identity())
    try:
        owner_type, owner_id = service.resolve_owner(meta["program_id"], meta["activity_id"], identity)
    except service.ResourceError as err:
        return jsonify(error="Validation failed", details={"program_id": [err.message]}), 400

    try:
        document = service.save_document(
            owner_type, owner_id, identity, request.files.get("file"),
            meta["category"], meta["title"],
            description=meta.get("description"), visibility=meta["visibility"], auto_verified=True,
        )
    except service.DocumentError as err:
        return jsonify(error="Validation failed", details={"file": [err.message]}), 400

    db.session.commit()
    return jsonify(resource=document.to_dict()), 201


def _resource_or_404(resource_id, role):
    document = db.session.get(Document, resource_id)
    if document is None or not service.can_view_resource(document, role):
        return None
    return document


@bp.get("/<int:resource_id>/file")
@jwt_required()
def download_resource(resource_id):
    role = get_jwt().get("role")
    document = _resource_or_404(resource_id, role)
    if document is None:
        return jsonify(error="Resource not found"), 404
    return send_file(document_file_path(document), mimetype=document.mime_type, download_name=document.original_filename)


@bp.delete("/<int:resource_id>")
@roles_required("admin", "staff")
def delete_resource(resource_id):
    document = get_or_404(Document, resource_id)
    if document.visibility is None:
        # A volunteer's own uploaded document, not a resource — this
        # endpoint never touches those (see documents/routes.py instead).
        return jsonify(error="Resource not found"), 404
    delete_document_file(document)
    db.session.delete(document)
    db.session.commit()
    return "", 204
