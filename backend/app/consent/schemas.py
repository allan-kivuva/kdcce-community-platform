from marshmallow import Schema, fields, validate

from ..models import CONSENT_STATUSES, CONSENT_TYPES


class ConsentCreateSchema(Schema):
    elderly_member_id = fields.Integer(required=True)
    consent_type = fields.String(required=True, validate=validate.OneOf(CONSENT_TYPES))
    status = fields.String(required=True, validate=validate.OneOf(CONSENT_STATUSES))
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    document_id = fields.Integer(load_default=None, allow_none=True)
