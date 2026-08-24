from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import ElderlyMember, Medication, MedicationAdministration
from ..utils import get_or_404, validation_error_response
from .schemas import MedicationAdministrationSchema, MedicationSchema

bp = Blueprint("medication", __name__, url_prefix="/api/medications")

schema = MedicationSchema()
administration_schema = MedicationAdministrationSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


@bp.post("")
@roles_required("admin", "staff")
def create_medication():
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    invalid = _member_or_400(data["elderly_member_id"])
    if invalid:
        return invalid

    data.setdefault("start_date", date.today())
    data.setdefault("status", "Active")
    medication = Medication(**data, created_by_id=int(get_jwt_identity()))
    db.session.add(medication)
    db.session.commit()
    return jsonify(medication=medication.to_dict()), 201


@bp.get("")
@roles_required("admin", "staff")
def list_medications():
    query = Medication.query
    elderly_member_id = request.args.get("elderly_member_id", type=int)
    if elderly_member_id:
        query = query.filter(Medication.elderly_member_id == elderly_member_id)
    status = request.args.get("status")
    if status:
        query = query.filter(Medication.status == status)

    medications = query.order_by(Medication.created_at.desc()).all()
    return jsonify(medications=[m.to_dict() for m in medications]), 200


@bp.get("/<int:medication_id>")
@roles_required("admin", "staff")
def get_medication(medication_id):
    medication = get_or_404(Medication, medication_id)
    return jsonify(medication=medication.to_dict()), 200


@bp.patch("/<int:medication_id>")
@roles_required("admin", "staff")
def update_medication(medication_id):
    medication = get_or_404(Medication, medication_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "elderly_member_id" in data:
        invalid = _member_or_400(data["elderly_member_id"])
        if invalid:
            return invalid

    for field, value in data.items():
        setattr(medication, field, value)
    db.session.commit()
    return jsonify(medication=medication.to_dict()), 200


@bp.delete("/<int:medication_id>")
@roles_required("admin")
def delete_medication(medication_id):
    medication = get_or_404(Medication, medication_id)
    db.session.delete(medication)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="This medication has administration records and cannot be deleted. Set its status to Discontinued instead."), 409
    return "", 204


# ---------- Administration log ----------

@bp.post("/<int:medication_id>/administrations")
@roles_required("admin", "staff")
def log_administration(medication_id):
    get_or_404(Medication, medication_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = administration_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    entry = MedicationAdministration(medication_id=medication_id, administered_by_id=int(get_jwt_identity()), **data)
    db.session.add(entry)
    db.session.commit()
    return jsonify(administration=entry.to_dict()), 201


@bp.get("/<int:medication_id>/administrations")
@roles_required("admin", "staff")
def list_administrations(medication_id):
    get_or_404(Medication, medication_id)
    entries = MedicationAdministration.query.filter_by(medication_id=medication_id).order_by(
        MedicationAdministration.administered_at.desc()
    ).all()
    return jsonify(administrations=[e.to_dict() for e in entries]), 200
