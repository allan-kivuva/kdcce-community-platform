from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Attendance, ElderlyMember, utcnow
from ..utils import get_or_404, validation_error_response
from .schemas import CheckInSchema, CheckOutSchema

bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")

check_in_schema = CheckInSchema()
check_out_schema = CheckOutSchema()


@bp.post("/check-in")
@roles_required("admin", "staff")
def check_in():
    payload = request.get_json(silent=True) or {}
    try:
        data = check_in_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    member = db.session.get(ElderlyMember, data["elderly_member_id"])
    if member is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400

    today = date.today()
    open_record = Attendance.query.filter_by(
        elderly_member_id=member.id, attendance_date=today, check_out_at=None
    ).first()
    if open_record is not None:
        return jsonify(error=f"{member.full_name} is already checked in today"), 409

    record = Attendance(
        elderly_member_id=member.id,
        attendance_date=today,
        recorded_by_id=int(get_jwt_identity()),
        notes=data.get("notes"),
    )
    db.session.add(record)
    db.session.commit()
    return jsonify(attendance=record.to_dict()), 201


@bp.patch("/<int:attendance_id>/check-out")
@roles_required("admin", "staff")
def check_out(attendance_id):
    record = get_or_404(Attendance, attendance_id)
    if record.check_out_at is not None:
        return jsonify(error="This attendance record is already checked out"), 409

    payload = request.get_json(silent=True) or {}
    try:
        data = check_out_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    record.check_out_at = utcnow()
    if data.get("notes"):
        record.notes = data["notes"]
    db.session.commit()
    return jsonify(attendance=record.to_dict()), 200


@bp.get("")
@roles_required("admin", "staff")
def list_attendance():
    query = Attendance.query
    date_str = request.args.get("date")
    if date_str:
        try:
            filter_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify(error="Validation failed", details={"date": ["Must be YYYY-MM-DD"]}), 400
        query = query.filter(Attendance.attendance_date == filter_date)

    elderly_member_id = request.args.get("elderly_member_id", type=int)
    if elderly_member_id:
        query = query.filter(Attendance.elderly_member_id == elderly_member_id)

    opa_id = request.args.get("opa_id", type=int)
    if opa_id:
        query = query.join(ElderlyMember).filter(ElderlyMember.opa_id == opa_id)

    records = query.order_by(Attendance.check_in_at.desc()).all()
    return jsonify(attendance=[r.to_dict() for r in records]), 200
