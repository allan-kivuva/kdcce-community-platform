from marshmallow import Schema, fields, validate

from ..models import BLOG_STATUSES

ALLOWED_TYPES = ("Story", "Skills", "Update")


class BlogPostSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    excerpt = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    image = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=500))
    type = fields.String(load_default="Story", validate=validate.OneOf(ALLOWED_TYPES))
    status = fields.String(load_default="Draft", validate=validate.OneOf(BLOG_STATUSES))
