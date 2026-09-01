from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import ElderlyMember, Meal, MealAttendance, Program
from ..utils import get_or_404, validation_error_response
from .schemas import MealAttendanceSchema, MealSchema

bp = Blueprint("feeding", __name__, url_prefix="/api/meals")

meal_schema = MealSchema()
attendance_schema = MealAttendanceSchema()


def _attendee_count(meal_id):
    return MealAttendance.query.filter_by(meal_id=meal_id).count()


def _program_or_400(program_id):
    if db.session.get(Program, program_id) is None:
        return jsonify(error="Validation failed", details={"program_id": ["Program not found"]}), 400
    return None


@bp.post("")
@roles_required("admin", "staff")
def create_meal():
    payload = request.get_json(silent=True) or {}
    try:
        data = meal_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)
    if data.get("program_id") is not None:
        invalid = _program_or_400(data["program_id"])
        if invalid:
            return invalid

    data.setdefault("meal_date", date.today())
    meal = Meal(**data, planned_by_id=int(get_jwt_identity()))
    db.session.add(meal)
    db.session.commit()
    return jsonify(meal=meal.to_dict(attendee_count=0)), 201


@bp.get("")
@roles_required("admin", "staff")
def list_meals():
    query = Meal.query
    date_str = request.args.get("date")
    if date_str:
        try:
            filter_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify(error="Validation failed", details={"date": ["Must be YYYY-MM-DD"]}), 400
        query = query.filter(Meal.meal_date == filter_date)
    meal_type = request.args.get("meal_type")
    if meal_type:
        query = query.filter(Meal.meal_type == meal_type)

    meals = query.order_by(Meal.meal_date.desc(), Meal.created_at.desc()).all()
    return jsonify(meals=[m.to_dict(attendee_count=_attendee_count(m.id)) for m in meals]), 200


@bp.get("/<int:meal_id>")
@roles_required("admin", "staff")
def get_meal(meal_id):
    meal = get_or_404(Meal, meal_id)
    return jsonify(meal=meal.to_dict(attendee_count=_attendee_count(meal.id))), 200


@bp.patch("/<int:meal_id>")
@roles_required("admin", "staff")
def update_meal(meal_id):
    meal = get_or_404(Meal, meal_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = meal_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)
    if data.get("program_id") is not None:
        invalid = _program_or_400(data["program_id"])
        if invalid:
            return invalid

    for field, value in data.items():
        setattr(meal, field, value)
    db.session.commit()
    return jsonify(meal=meal.to_dict(attendee_count=_attendee_count(meal.id))), 200


@bp.delete("/<int:meal_id>")
@roles_required("admin")
def delete_meal(meal_id):
    meal = get_or_404(Meal, meal_id)
    db.session.delete(meal)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="This meal has recorded attendance and cannot be deleted."), 409
    return "", 204


# ---------- Attendance ----------

@bp.post("/<int:meal_id>/attendance")
@roles_required("admin", "staff")
def mark_attendance(meal_id):
    get_or_404(Meal, meal_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = attendance_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    if db.session.get(ElderlyMember, data["elderly_member_id"]) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400

    existing = MealAttendance.query.filter_by(meal_id=meal_id, elderly_member_id=data["elderly_member_id"]).first()
    if existing is not None:
        return jsonify(error="This member is already recorded for this meal"), 409

    record = MealAttendance(meal_id=meal_id, elderly_member_id=data["elderly_member_id"], notes=data.get("notes"), recorded_by_id=int(get_jwt_identity()))
    db.session.add(record)
    db.session.commit()
    return jsonify(attendance=record.to_dict()), 201


@bp.get("/<int:meal_id>/attendance")
@roles_required("admin", "staff")
def list_attendance(meal_id):
    get_or_404(Meal, meal_id)
    records = MealAttendance.query.filter_by(meal_id=meal_id).order_by(MealAttendance.created_at.asc()).all()
    return jsonify(attendance=[r.to_dict() for r in records]), 200
