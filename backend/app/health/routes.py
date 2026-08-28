from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..followups.service import create_from_source
from ..models import ElderlyMember, HealthRecord, utcnow
from ..utils import get_or_404, validation_error_response
from .schemas import HealthRecordSchema

bp = Blueprint("health", __name__, url_prefix="/api/health-records")

schema = HealthRecordSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


@bp.post("")
@roles_required("admin", "staff")
def create_record():
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    invalid = _member_or_400(data["elderly_member_id"])
    if invalid:
        return invalid

    data.setdefault("follow_up_required", False)
    record = HealthRecord(**data, recorded_by_id=int(get_jwt_identity()))
    if record.recorded_at is None:
        record.recorded_at = utcnow()
    db.session.add(record)
    db.session.flush()  # assigns record.id so a follow-up can reference it
    if record.follow_up_required:
        create_from_source(
            record.elderly_member_id, "health_record", record.id,
            record.follow_up_notes or "Follow-up required after a health observation.",
            int(get_jwt_identity()),
        )
    db.session.commit()
    return jsonify(record=record.to_dict()), 201


@bp.get("")
@roles_required("admin", "staff")
def list_records():
    query = HealthRecord.query
    elderly_member_id = request.args.get("elderly_member_id", type=int)
    if elderly_member_id:
        query = query.filter(HealthRecord.elderly_member_id == elderly_member_id)
    follow_up_required = request.args.get("follow_up_required")
    if follow_up_required is not None:
        query = query.filter(HealthRecord.follow_up_required == (follow_up_required.lower() == "true"))

    records = query.order_by(HealthRecord.recorded_at.desc()).all()
    return jsonify(records=[r.to_dict() for r in records]), 200


@bp.get("/<int:record_id>")
@roles_required("admin", "staff")
def get_record(record_id):
    record = get_or_404(HealthRecord, record_id)
    return jsonify(record=record.to_dict()), 200


@bp.patch("/<int:record_id>")
@roles_required("admin", "staff")
def update_record(record_id):
    record = get_or_404(HealthRecord, record_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "elderly_member_id" in data:
        invalid = _member_or_400(data["elderly_member_id"])
        if invalid:
            return invalid

    was_follow_up_required = record.follow_up_required
    for field, value in data.items():
        setattr(record, field, value)

    if record.follow_up_required and not was_follow_up_required:
        create_from_source(
            record.elderly_member_id, "health_record", record.id,
            record.follow_up_notes or "Follow-up required after a health observation.",
            int(get_jwt_identity()),
        )

    db.session.commit()
    return jsonify(record=record.to_dict()), 200


@bp.delete("/<int:record_id>")
@roles_required("admin")
def delete_record(record_id):
    record = get_or_404(HealthRecord, record_id)
    db.session.delete(record)
    db.session.commit()
    return "", 204
