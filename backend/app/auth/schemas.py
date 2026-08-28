from marshmallow import Schema, fields, validate

from ..models import ROLES

# Public self-signup is always a volunteer — role is never taken from the client
# for anything higher-privileged than that.
ALLOWED_SELF_SIGNUP_ROLES = ("volunteer",)


class RegisterSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=1))
