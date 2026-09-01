import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..campaigns.service import find_campaign_by_exact_name
from ..donors.service import resolve_or_create_donor
from ..extensions import db, limiter
from ..models import Campaign, Donation, Donor
from ..utils import get_or_404, validation_error_response, csv_response
from .schemas import AdminDonationCreateSchema, DonationCreateSchema, DonationUpdateSchema

bp = Blueprint("donations", __name__, url_prefix="/api/donations")
# Separate blueprint (not nested under /api/donations) so this endpoint's
# path can live at /api/admin/donations, matching the existing
# /api/admin/<module> convention used by blog/gallery/team/crafts for
# staff-only writes — without touching any of bp's existing route paths.
admin_bp = Blueprint("admin_donations", __name__, url_prefix="/api/admin/donations")

create_schema = DonationCreateSchema()
admin_create_schema = AdminDonationCreateSchema()
update_schema = DonationUpdateSchema()


def _make_txn_id():
    return f"TXN-{secrets.token_hex(6).upper()}"


def _assign_receipt_and_commit(donation):
    db.session.add(donation)
    db.session.flush()  # assigns donation.id without committing yet
    year = datetime.now(timezone.utc).year
    donation.receipt_id = f"KDCCE-{year}-{str(donation.id).zfill(6)}"
    donation.txn_id = _make_txn_id()

    # Phase 6: link this new donation to a Donor/Campaign wherever that's
    # unambiguous, without touching the free-text donor_name/donor_email/
    # campaign fields at all. Both are deterministic single-candidate
    # lookups (the donor's own email just typed on this submission; an
    # exact-name Campaign match) — not the ambiguous multi-candidate
    # problem the historical backfill guards against. See donors/service.py
    # and campaigns/service.py for the exact rules.
    donor = resolve_or_create_donor(donation.donor_name, donation.donor_email)
    donation.donor_id = donor.id if donor else None
    matched_campaign = find_campaign_by_exact_name(donation.campaign)
    donation.campaign_id = matched_campaign.id if matched_campaign else None

    db.session.commit()


@bp.post("")
@limiter.limit("10 per minute")
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
        donation_type="Cash",
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
    _assign_receipt_and_commit(donation)
    return jsonify(donation=donation.to_dict()), 201


@admin_bp.post("")
@roles_required("admin", "staff")
def create_admin_donation():
    """Staff/admin logging a donation received in person — any type. This
    is the only way a Food/Equipment donation gets created; there is no
    public in-kind form."""
    payload = request.get_json(silent=True) or {}
    try:
        data = admin_create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    is_cash = data["donation_type"] == "Cash"
    donation = Donation(
        donation_type=data["donation_type"],
        donor_name=data["donor_name"].strip(),
        donor_email=(data.get("donor_email") or "").lower() or None,
        donor_phone=data.get("donor_phone"),
        amount=data.get("amount"),
        currency=data.get("currency") or "KES",
        frequency="one-time",
        campaign=data.get("campaign"),
        payment_method=data.get("payment_method") if is_cash else None,
        item_description=data.get("item_description"),
        quantity=data.get("quantity"),
        unit=data.get("unit"),
        status="Paid" if is_cash else "Received",
        message=data.get("message"),
        txn_id="",
        receipt_id="",
    )
    _assign_receipt_and_commit(donation)
    return jsonify(donation=donation.to_dict()), 201


@bp.get("")
@roles_required("admin", "staff")
def list_donations():
    query = Donation.query
    donation_type = request.args.get("donation_type")
    if donation_type:
        query = query.filter(Donation.donation_type == donation_type)
    donations = query.order_by(Donation.created_at.desc()).all()
    return jsonify(donations=[d.to_dict() for d in donations]), 200


@bp.get("/export.csv")
@roles_required("admin", "staff")
def export_donations_csv():
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    headers = [
        "Donor", "Email", "Amount", "Currency", "Frequency", "Campaign", "Payment Method",
        "Status", "Transaction ID", "Receipt ID", "Date",
        "Type", "Item Description", "Quantity", "Unit",
    ]
    rows = [
        [
            d.donor_name, d.donor_email or "", float(d.amount) if d.amount is not None else "", d.currency, d.frequency,
            d.campaign or "", d.payment_method or "", d.status, d.txn_id, d.receipt_id,
            d.created_at.isoformat(),
            d.donation_type, d.item_description or "", float(d.quantity) if d.quantity is not None else "", d.unit or "",
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

    if "donor_id" in data and data["donor_id"] is not None and db.session.get(Donor, data["donor_id"]) is None:
        return jsonify(error="Validation failed", details={"donor_id": ["Donor not found"]}), 400
    if "campaign_id" in data and data["campaign_id"] is not None and db.session.get(Campaign, data["campaign_id"]) is None:
        return jsonify(error="Validation failed", details={"campaign_id": ["Campaign not found"]}), 400

    previous_status = donation.status
    for field, value in data.items():
        if field == "donor_email" and value is not None:
            value = value.lower()
        setattr(donation, field, value)
    db.session.flush()

    # A donation-status change is exactly the kind of "manual financial
    # correction" this phase's audit requirements call out — logged
    # distinctly from an ordinary field edit.
    if "status" in data and data["status"] != previous_status:
        log_action(
            int(get_jwt_identity()), "status_change", "donation", donation.id,
            before={"status": previous_status}, after={"status": donation.status},
        )
    db.session.commit()
    return jsonify(donation=donation.to_dict()), 200
