from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..achievements.service import check_and_award
from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import TrainingCourse, TrainingProgress, VolunteerProfile, utcnow
from ..notifications.service import notify
from ..utils import get_or_404, validation_error_response
from .schemas import TrainingCourseCreateSchema, TrainingCourseUpdateSchema, TrainingProgressUpdateSchema

bp = Blueprint("training", __name__, url_prefix="/api/training")

_SNAPSHOT_FIELDS = ("title", "category", "required", "active", "estimated_minutes")


def _snapshot(course):
    snapshot = {}
    for field in _SNAPSHOT_FIELDS:
        value = getattr(course, field)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        snapshot[field] = value
    return snapshot


create_schema = TrainingCourseCreateSchema()
update_schema = TrainingCourseUpdateSchema()
progress_schema = TrainingProgressUpdateSchema()


def _my_profile_or_404():
    profile = VolunteerProfile.query.filter_by(user_id=int(get_jwt_identity())).first()
    if profile is None:
        return None, (jsonify(error="No volunteer profile on this account"), 404)
    return profile, None


@bp.get("")
@jwt_required()
def list_courses():
    role = get_jwt().get("role")
    query = TrainingCourse.query
    if role not in ("admin", "staff") or request.args.get("include_inactive") != "true":
        query = query.filter(TrainingCourse.active.is_(True))
    courses = query.order_by(TrainingCourse.required.desc(), TrainingCourse.title.asc()).all()
    return jsonify(courses=[c.to_dict() for c in courses]), 200


@bp.get("/<int:course_id>")
@jwt_required()
def get_course(course_id):
    course = get_or_404(TrainingCourse, course_id)
    return jsonify(course=course.to_dict()), 200


@bp.post("")
@roles_required("admin", "staff")
def create_course():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)
    course = TrainingCourse(**data, created_by_id=int(get_jwt_identity()))
    db.session.add(course)
    db.session.flush()
    log_action(int(get_jwt_identity()), "create", "training_course", course.id, after=_snapshot(course))
    db.session.commit()
    return jsonify(course=course.to_dict()), 201


@bp.patch("/<int:course_id>")
@roles_required("admin", "staff")
def update_course(course_id):
    course = get_or_404(TrainingCourse, course_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)
    before = _snapshot(course)
    for field, value in data.items():
        setattr(course, field, value)
    after = _snapshot(course)
    if after != before:
        log_action(int(get_jwt_identity()), "update", "training_course", course.id, before=before, after=after)
    db.session.commit()
    return jsonify(course=course.to_dict()), 200


@bp.get("/<int:course_id>/completions")
@roles_required("admin", "staff")
def list_course_completions(course_id):
    get_or_404(TrainingCourse, course_id)
    rows = TrainingProgress.query.filter_by(course_id=course_id).order_by(TrainingProgress.updated_at.desc()).all()
    return jsonify(completions=[
        {**row.to_dict(), "volunteer_name": row.volunteer_profile.user.name, "volunteer_profile_id": row.volunteer_profile_id}
        for row in rows
    ]), 200


# ---------- Volunteer self-service progress ----------

def _courses_with_progress(volunteer_profile_id):
    """Every active course, merged with one volunteer's own progress row
    if one exists — defaulting to "Not Started" if not, same "synthesize
    the full list, only store the exception" pattern as the assignment
    checklist. Required courses sort first. Shared by the volunteer's own
    /me/progress view and the admin/staff per-volunteer view below —
    same merge, just parameterized by whose profile it's for."""
    courses = TrainingCourse.query.filter_by(active=True).order_by(TrainingCourse.required.desc(), TrainingCourse.title.asc()).all()
    progress_by_course = {p.course_id: p for p in TrainingProgress.query.filter_by(volunteer_profile_id=volunteer_profile_id).all()}
    result = []
    for course in courses:
        entry = course.to_dict()
        progress = progress_by_course.get(course.id)
        entry["progress"] = progress.to_dict() if progress else {"status": "Not Started", "started_at": None, "completed_at": None}
        result.append(entry)
    return result


@bp.get("/me/progress")
@jwt_required()
def list_my_progress():
    profile, err = _my_profile_or_404()
    if err:
        return err
    return jsonify(courses=_courses_with_progress(profile.id)), 200


@bp.patch("/me/progress/<int:course_id>")
@jwt_required()
def update_my_progress(course_id):
    profile, err = _my_profile_or_404()
    if err:
        return err
    course = get_or_404(TrainingCourse, course_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = progress_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    progress = TrainingProgress.query.filter_by(course_id=course.id, volunteer_profile_id=profile.id).first()
    if progress is None:
        progress = TrainingProgress(course_id=course.id, volunteer_profile_id=profile.id)
        db.session.add(progress)

    new_status = data["status"]
    if new_status == "In Progress" and progress.started_at is None:
        progress.started_at = utcnow()
    if new_status == "Completed" and progress.completed_at is None:
        progress.completed_at = utcnow()
        if progress.started_at is None:
            progress.started_at = progress.completed_at
    progress.status = new_status
    db.session.flush()

    if new_status == "Completed":
        check_and_award(int(get_jwt_identity()), profile.id)

    db.session.commit()
    return jsonify(progress=progress.to_dict()), 200
