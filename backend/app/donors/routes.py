from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Donor
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import DonorCreateSchema, DonorUpdateSchema

bp = Blueprint("donors", __name__, url_prefix="/api/donors")

create_schema = DonorCreateSchema()
update_schema = DonorUpdateSchema()

_SNAPSHOT_FIELDS = ("name", "email", "phone", "organization", "donor_type", "notes", "active")


def _snapshot(donor):
    return {field: getattr(donor, field) for field in _SNAPSHOT_FIELDS}


@bp.get("")
@roles_required("admin", "staff")
def list_donors():
    query = Donor.query
    q = request.args.get("q")
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.filter(db.or_(db.func.lower(Donor.name).like(like), db.func.lower(Donor.email).like(like)))
    donor_type = request.args.get("donor_type")
    if donor_type:
        query = query.filter_by(donor_type=donor_type)
    donors = query.order_by(Donor.name.asc()).all()
    return jsonify(donors=[d.to_dict() for d in donors]), 200


@bp.post("")
@roles_required("admin", "staff")
def create_donor():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)
    if data.get("email"):
        data["email"] = data["email"].strip().lower()

    donor = Donor(**data)
    db.session.add(donor)
    db.session.flush()
    log_action(int(get_jwt_identity()), "create", "donor", donor.id, after=_snapshot(donor))
    db.session.commit()
    return jsonify(donor=donor.to_dict()), 201


@bp.get("/<int:donor_id>")
@roles_required("admin", "staff")
def get_donor(donor_id):
    donor = get_or_404(Donor, donor_id)
    stats = service.donor_stats(donor)
    return jsonify(
        donor=donor.to_dict(
            lifetime_amount=stats["lifetime_amount"], donation_count=stats["donation_count"],
            most_recent_donation_at=stats["most_recent_donation_at"], campaigns_supported=stats["campaigns_supported"],
        ),
        donations=[d.to_dict() for d in stats["donations"]],
    ), 200


@bp.patch("/<int:donor_id>")
@roles_required("admin", "staff")
def update_donor(donor_id):
    donor = get_or_404(Donor, donor_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)
    if "email" in data and data["email"]:
        data["email"] = data["email"].strip().lower()

    before = _snapshot(donor)
    for field, value in data.items():
        setattr(donor, field, value)
    db.session.flush()
    log_action(int(get_jwt_identity()), "update", "donor", donor.id, before=before, after=_snapshot(donor))
    db.session.commit()
    return jsonify(donor=donor.to_dict()), 200
