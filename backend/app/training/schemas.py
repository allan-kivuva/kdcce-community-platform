from marshmallow import Schema, fields, validate

from ..models import TRAINING_PROGRESS_STATUSES


class TrainingCourseCreateSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=150))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))
    category = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=60))
    resource_url = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=500))
    estimated_minutes = fields.Integer(load_default=None, allow_none=True, validate=validate.Range(min=1))
    required = fields.Boolean(load_default=False)


class TrainingCourseUpdateSchema(Schema):
    """Full edit — admin/staff only. No load_default on `required`: a
    meaningful non-null default only applies at creation, not on a
    partial edit that happens to omit the field (same principle used
    throughout this app's other *StaffUpdateSchema classes)."""

    title = fields.String(validate=validate.Length(min=1, max=150))
    description = fields.String(allow_none=True, validate=validate.Length(max=2000))
    category = fields.String(allow_none=True, validate=validate.Length(max=60))
    resource_url = fields.String(allow_none=True, validate=validate.Length(max=500))
    estimated_minutes = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    required = fields.Boolean()
    active = fields.Boolean()


class TrainingProgressUpdateSchema(Schema):
    # "Not Started" excluded on purpose — a volunteer can only move
    # forward (start or complete); there's no client action that should
    # ever reset progress backward to Not Started.
    status = fields.String(required=True, validate=validate.OneOf(("In Progress", "Completed")))
