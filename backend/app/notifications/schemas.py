from marshmallow import Schema, fields


class NotificationUpdateSchema(Schema):
    """The only thing a recipient can change about their own notification
    — no title/message/type field exists here, so there's no way to edit
    the notification's content, only its read state."""

    is_read = fields.Boolean(required=True)
