from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from . import service

bp = Blueprint("imports", __name__, url_prefix="/api/imports")


def _entity_or_400(entity):
    if entity not in service.ENTITIES:
        return jsonify(error="Validation failed", details={"entity": [f"Must be one of: {', '.join(service.ENTITIES)}"]}), 400
    return None


def _file_or_400():
    file_storage = request.files.get("file")
    if file_storage is None or file_storage.filename == "":
        return None, (jsonify(error="Validation failed", details={"file": ["A CSV file is required"]}), 400)
    if not file_storage.filename.lower().endswith(".csv"):
        return None, (jsonify(error="Validation failed", details={"file": ["Must be a .csv file"]}), 400)
    return file_storage, None


@bp.post("/<entity>/preview")
@roles_required("admin", "staff")
def preview_import(entity):
    bad_entity = _entity_or_400(entity)
    if bad_entity:
        return bad_entity
    file_storage, error = _file_or_400()
    if error:
        return error

    try:
        result = service.preview(entity, file_storage)
    except service.ImportError_ as err:
        return jsonify(error=str(err)), 400
    return jsonify(result), 200


@bp.post("/<entity>/commit")
@roles_required("admin", "staff")
def commit_import(entity):
    """Re-validates the SAME file server-side — this is not a
    "trust the preview" endpoint. Every commit is audited with a row
    count summary, never the raw file contents (which may include
    sensitive free text like elderly member notes)."""
    bad_entity = _entity_or_400(entity)
    if bad_entity:
        return bad_entity
    file_storage, error = _file_or_400()
    if error:
        return error

    identity = int(get_jwt_identity())
    try:
        result = service.commit(entity, file_storage, identity)
    except service.ImportError_ as err:
        db.session.rollback()
        return jsonify(error=str(err)), 400

    log_action(
        identity, "import", entity, result["created_count"],
        after={"filename": file_storage.filename, "created_count": result["created_count"], "skipped_count": len(result["skipped"]), "total": result["total"]},
    )
    db.session.commit()
    return jsonify(result), 200
