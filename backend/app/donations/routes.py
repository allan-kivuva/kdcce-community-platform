import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Donation
from ..utils import get_or_404, validation_error_response, csv_response
from .schemas import DonationCreateSchema, DonationUpdateSchema

bp = Blueprint("donations", __name__, url_prefix="/api/donations")

create_schema = DonationCreateSchema()
update_schema = DonationUpdateSchema()


def _make_txn_id():
    return f"TXN-{secrets.token_hex(6).upper()}"


@bp.post("")
def create_donation():
    """Public, unauthenticated: this is the donor-facing donation form.
    There is no real payment gateway behind this yet — see the note on
    Donation.status in models.py. The server always assigns status,
    txn_id and receipt_id; none of those are accepted from the client."""
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    donation = Donation(
        donor_name=data["donor_name"].strip(),
        donor_email=data["donor_email"].lower(),
        donor_phone=data.get("donor_phone"),
        amount=data["amount"],
        currency=data.get("currency") or "KES",
        frequency=data["frequency"],
        campaign=data.get("campaign"),
        payment_method=data.get("payment_method"),
        status="Paid",
        message=data.get("message"),
        txn_id="",
        receipt_id="",
    )
    db.session.add(donation)
    db.session.flush()  # assigns donation.id without committing yet

    year = datetime.now(timezone.utc).year
    donation.receipt_id = f"KDCCE-{year}-{str(donation.id).zfill(6)}"
    donation.txn_id = _make_txn_id()
    db.session.commit()

    return jsonify(donation=donation.to_dict()), 201


@bp.get("")
@roles_required("admin", "staff")
def list_donations():
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    return jsonify(donations=[d.to_dict() for d in donations]), 200


@bp.get("/export.csv")
@roles_required("admin", "staff")
def export_donations_csv():
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    headers = ["Donor", "Email", "Amount", "Currency", "Frequency", "Campaign", "Payment Method", "Status", "Transaction ID", "Receipt ID", "Date"]
    rows = [
        [
            d.donor_name, d.donor_email, float(d.amount), d.currency, d.frequency,
            d.campaign or "", d.payment_method or "", d.status, d.txn_id, d.receipt_id,
            d.created_at.isoformat(),
        ]
        for d in donations
    ]
    return csv_response("donations.csv", headers, rows)


@bp.get("/<int:donation_id>")
@roles_required("admin", "staff")
def get_donation(donation_id):
    donation = get_or_404(Donation, donation_id)
    return jsonify(donation=donation.to_dict()), 200


@bp.patch("/<int:donation_id>")
@roles_required("admin", "staff")
def update_donation(donation_id):
    donation = get_or_404(Donation, donation_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    for field, value in data.items():
        if field == "donor_email" and value is not None:
            value = value.lower()
        setattr(donation, field, value)

    db.session.commit()
    return jsonify(donation=donation.to_dict()), 200
