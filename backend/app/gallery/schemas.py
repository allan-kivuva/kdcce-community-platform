from marshmallow import Schema, fields, validate


class GalleryImageSchema(Schema):
    url = fields.String(required=True, validate=validate.Length(min=1, max=500))
    caption = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=200))
