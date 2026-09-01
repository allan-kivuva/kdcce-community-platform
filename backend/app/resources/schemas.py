from marshmallow import Schema, fields, validate

from ..models import RESOURCE_VISIBILITIES

RESOURCE_CATEGORIES = (
    "Program Guide", "Volunteer Instructions", "Policy", "Event Material", "Training Reference", "Form", "Other",
)


class ResourceUploadMetaSchema(Schema):
    """Metadata alongside the uploaded file — multipart form fields
    arrive as strings, same reasoning as DocumentUploadMetaSchema in
    volunteers/schemas.py, so program_id/activity_id are parsed as
    optional integer strings."""

    title = fields.String(required=True, validate=validate.Length(min=1, max=150))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    category = fields.String(load_default="Other", validate=validate.OneOf(RESOURCE_CATEGORIES))
    visibility = fields.String(load_default="Volunteers", validate=validate.OneOf(RESOURCE_VISIBILITIES))
    program_id = fields.Integer(load_default=None, allow_none=True)
    activity_id = fields.Integer(load_default=None, allow_none=True)
