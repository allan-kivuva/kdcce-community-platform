from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from ..models import COMMUNICATION_AUDIENCES


class BroadcastCreateSchema(Schema):
    audience_type = fields.String(required=True, validate=validate.OneOf(COMMUNICATION_AUDIENCES))
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    message = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    selected_user_ids = fields.List(fields.Integer(), load_default=None, allow_none=True)
    client_token = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=64))

    @validates_schema
    def validate_audience(self, data, **kwargs):
        if data["audience_type"] == "Selected" and not data.get("selected_user_ids"):
            raise ValidationError({"selected_user_ids": ["Required when audience_type is Selected"]})
