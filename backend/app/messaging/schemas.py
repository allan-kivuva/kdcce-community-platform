from marshmallow import Schema, fields, validate


class ConversationCreateSchema(Schema):
    """Starting a conversation always sends its first message in the same
    call — there is no such thing as an empty conversation in this app,
    which keeps last_message_at non-null for every real conversation and
    avoids a NULLS-LAST ordering edge case entirely."""

    recipient_id = fields.Integer(required=True)
    body = fields.String(required=True, validate=validate.Length(min=1, max=4000))
    # Only meaningful (and only ever honored) when the caller is a
    # family account — see messaging/routes.py:create_conversation().
    # Ignored for every other role.
    elderly_member_id = fields.Integer(load_default=None, allow_none=True)


class DirectMessageCreateSchema(Schema):
    body = fields.String(required=True, validate=validate.Length(min=1, max=4000))
