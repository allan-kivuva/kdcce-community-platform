from marshmallow import Schema, fields, validate


class TeamMemberSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    role = fields.String(required=True, validate=validate.Length(min=1, max=120))
    image = fields.String(required=True, validate=validate.Length(min=1, max=500))
