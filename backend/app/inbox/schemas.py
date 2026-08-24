from marshmallow import Schema, fields, validate


class InboxMessageCreateSchema(Schema):
    """Used by the public POST /api/inbox endpoint — the contact form.
    is_read is always server-set (False); never accepted from the client."""

    name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    email = fields.Email(required=True)
    subject = fields.String(required=True, validate=validate.Length(min=1, max=200))
    message = fields.String(required=True, validate=validate.Length(min=1, max=5000))


class InboxMessageUpdateSchema(Schema):
    is_read = fields.Boolean(required=True)
