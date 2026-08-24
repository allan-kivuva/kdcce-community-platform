from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import BlogPost
from ..utils import get_or_404, validation_error_response
from .schemas import BlogPostSchema

bp = Blueprint("blog", __name__)

schema = BlogPostSchema()


@bp.get("/api/blog")
def list_public_posts():
    posts = BlogPost.query.filter_by(status="Published").order_by(BlogPost.created_at.desc()).all()
    return jsonify(posts=[p.to_dict() for p in posts]), 200


@bp.get("/api/admin/blog")
@roles_required("admin", "staff")
def list_all_posts():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return jsonify(posts=[p.to_dict() for p in posts]), 200


@bp.post("/api/admin/blog")
@roles_required("admin", "staff")
def create_post():
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    post = BlogPost(**data)
    db.session.add(post)
    db.session.commit()
    return jsonify(post=post.to_dict()), 201


@bp.patch("/api/admin/blog/<int:post_id>")
@roles_required("admin", "staff")
def update_post(post_id):
    post = get_or_404(BlogPost, post_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    for field, value in data.items():
        setattr(post, field, value)
    db.session.commit()
    return jsonify(post=post.to_dict()), 200


@bp.delete("/api/admin/blog/<int:post_id>")
@roles_required("admin", "staff")
def delete_post(post_id):
    post = get_or_404(BlogPost, post_id)
    db.session.delete(post)
    db.session.commit()
    return "", 204
