from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from ..models import DAYS_OF_WEEK, DOCUMENT_TYPES, VOLUNTEER_HOURS_CATEGORIES, VOLUNTEER_HOURS_STATUSES, VOLUNTEER_STATUSES


class VolunteerSelfUpdateSchema(Schema):
    """What a volunteer may change on their own profile/application — never
    status, reviewed_by, reviewed_at, or rejection_reason. Used both for
    the initial application (immediately after registration) and for later
    self-service edits — the same fields are editable either way."""

    phone = fields.String(allow_none=True, validate=validate.Length(max=40))
    skills = fields.String(allow_none=True, validate=validate.Length(max=1000))
    availability = fields.String(allow_none=True, validate=validate.Length(max=1000))
    areas_of_interest = fields.String(allow_none=True, validate=validate.Length(max=1000))
    experience = fields.String(allow_none=True, validate=validate.Length(max=2000))
    motivation = fields.String(allow_none=True, validate=validate.Length(max=2000))
    bio = fields.String(allow_none=True, validate=validate.Length(max=2000))
    # Phase 8: optional self-set location preference, used only as a
    # distance input to smart matching (see matching/service.py) — never
    # required, never derived from anything else on this profile.
    latitude = fields.Float(allow_none=True, validate=validate.Range(min=-90, max=90))
    longitude = fields.Float(allow_none=True, validate=validate.Range(min=-180, max=180))


class VolunteerStaffUpdateSchema(VolunteerSelfUpdateSchema):
    """Staff/admin can additionally verify or reject a volunteer, and
    record why on a rejection. rejection_reason is accepted regardless of
    which way status is set — the route clears it on any non-Rejected
    status so a stale reason from a previous rejection can't linger past
    a later reversal."""

    status = fields.String(allow_none=False, validate=validate.OneOf(VOLUNTEER_STATUSES))
    rejection_reason = fields.String(allow_none=True, validate=validate.Length(max=2000))


class VolunteerAvailabilityCreateSchema(Schema):
    day_of_week = fields.String(required=True, validate=validate.OneOf(DAYS_OF_WEEK))
    start_time = fields.Time(required=True)
    end_time = fields.Time(required=True)

    @validates_schema
    def validate_times(self, data, **kwargs):
        if data["end_time"] <= data["start_time"]:
            raise ValidationError({"end_time": ["Must be after start_time"]})


class VolunteerUnavailabilityCreateSchema(Schema):
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    reason = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=200))

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["end_date"] < data["start_date"]:
            raise ValidationError({"end_date": ["Must not be before start_date"]})


class ManualHoursCreateSchema(Schema):
    date = fields.Date(required=True)
    duration_minutes = fields.Integer(required=True, validate=validate.Range(min=1, max=24 * 60))
    category = fields.String(load_default="Other", validate=validate.OneOf(VOLUNTEER_HOURS_CATEGORIES))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))

    @validates_schema
    def validate_not_future(self, data, **kwargs):
        from datetime import date as _date
        if data["date"] > _date.today():
            raise ValidationError({"date": ["Cannot log hours for a future date"]})


class ManualHoursReviewSchema(Schema):
    """Admin/staff only — approve or reject a submitted entry. Never lets
    the submitter's own fields (date/duration/category/description) be
    edited here; a wrong entry is rejected and resubmitted, not silently
    rewritten by someone else."""

    status = fields.String(required=True, validate=validate.OneOf(("Approved", "Rejected")))
    rejection_reason = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2000))


class RecognitionCreateSchema(Schema):
    achievement_id = fields.Integer(required=True)
    notes = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=1000))


class DocumentUploadMetaSchema(Schema):
    """The non-file fields alongside a multipart document upload — the
    file itself comes through request.files, same split as assignment
    photos (which have no metadata at all, just the file)."""

    document_type = fields.String(required=True, validate=validate.OneOf(DOCUMENT_TYPES))
    title = fields.String(required=True, validate=validate.Length(min=1, max=150))
    issue_date = fields.Date(load_default=None, allow_none=True)
    expiry_date = fields.Date(load_default=None, allow_none=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data.get("issue_date") and data.get("expiry_date") and data["expiry_date"] < data["issue_date"]:
            raise ValidationError({"expiry_date": ["Must not be before issue_date"]})


class QrVerifySchema(Schema):
    token = fields.String(required=True, validate=validate.Length(min=1, max=2000))
