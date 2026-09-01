from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from ..models import ANNOUNCEMENT_PRIORITIES, COMMUNICATION_AUDIENCES


class AnnouncementCreateSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    body = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    priority = fields.String(load_default="Normal", validate=validate.OneOf(ANNOUNCEMENT_PRIORITIES))
    audience_type = fields.String(required=True, validate=validate.OneOf(COMMUNICATION_AUDIENCES))
    selected_user_ids = fields.List(fields.Integer(), load_default=None, allow_none=True)
    publish_at = fields.DateTime(load_default=None, allow_none=True)
    expires_at = fields.DateTime(load_default=None, allow_none=True)

    @validates_schema
    def validate_audience_and_dates(self, data, **kwargs):
        if data["audience_type"] == "Selected" and not data.get("selected_user_ids"):
            raise ValidationError({"selected_user_ids": ["Required when audience_type is Selected"]})
        if data.get("publish_at") and data.get("expires_at") and data["expires_at"] <= data["publish_at"]:
            raise ValidationError({"expires_at": ["Must be after publish_at"]})


class AnnouncementUpdateSchema(Schema):
    """Partial edit — no load_default on any field, same principle as
    every other *UpdateSchema in this app: a field simply absent from
    the payload must never silently overwrite existing data with a
    default."""

    title = fields.String(validate=validate.Length(min=1, max=200))
    body = fields.String(validate=validate.Length(min=1, max=5000))
    priority = fields.String(validate=validate.OneOf(ANNOUNCEMENT_PRIORITIES))
    audience_type = fields.String(validate=validate.OneOf(COMMUNICATION_AUDIENCES))
    selected_user_ids = fields.List(fields.Integer(), allow_none=True)
    publish_at = fields.DateTime(allow_none=True)
    expires_at = fields.DateTime(allow_none=True)
    active = fields.Boolean()

    @validates_schema
    def validate_audience(self, data, **kwargs):
        if data.get("audience_type") == "Selected" and "selected_user_ids" in data and not data.get("selected_user_ids"):
            raise ValidationError({"selected_user_ids": ["Required when audience_type is Selected"]})
