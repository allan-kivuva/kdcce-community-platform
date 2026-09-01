from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class DocumentStatusUpdateSchema(Schema):
    status = fields.String(required=True, validate=validate.OneOf(("Verified", "Rejected")))
    rejection_reason = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))

    @validates_schema
    def validate_reason(self, data, **kwargs):
        if data["status"] == "Rejected" and not data.get("rejection_reason"):
            raise ValidationError({"rejection_reason": ["Required when rejecting a document"]})
