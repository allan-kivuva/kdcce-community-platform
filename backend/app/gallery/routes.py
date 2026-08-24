from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import GalleryImage
from ..utils import get_or_404, validation_error_response
from .schemas import GalleryImageSchema

bp = Blueprint("gallery", __name__)

schema = GalleryImageSchema()


@bp.get("/api/gallery")
def list_images():
    images = GalleryImage.query.order_by(GalleryImage.created_at.desc()).all()
    return jsonify(images=[i.to_dict() for i in images]), 200


@bp.post("/api/admin/gallery")
@roles_required("admin", "staff")
def create_image():
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    image = GalleryImage(**data)
    db.session.add(image)
    db.session.commit()
    return jsonify(image=image.to_dict()), 201


@bp.delete("/api/admin/gallery/<int:image_id>")
@roles_required("admin", "staff")
def delete_image(image_id):
    image = get_or_404(GalleryImage, image_id)
    db.session.delete(image)
    db.session.commit()
    return "", 204
