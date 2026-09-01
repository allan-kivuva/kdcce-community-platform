from ..extensions import db
from ..models import Donation, DONATION_COUNTED_STATUSES, Donor


def normalize_email(email):
    return email.strip().lower() if email else None


def resolve_or_create_donor(name, email, phone=None, donor_type="Individual"):
    """Called at donation-creation time (both the public Cash form and
    the staff in-kind form) — not the same problem as the migration
    backfill's historical-ambiguity handling. Here there is exactly one
    candidate: whatever email the donor/staff typed on THIS submission.
    If it matches an existing Donor by normalized email, that donation is
    attributed to them (a repeat donor may phrase their name slightly
    differently each time — the email is the identity key, the name on
    file is not overwritten). If there's no email at all, no donor is
    resolved or created — an anonymous/no-contact in-kind gift stays
    donor_id=None, exactly as before Phase 6."""
    normalized = normalize_email(email)
    if not normalized:
        return None
    existing = Donor.query.filter_by(email=normalized).first()
    if existing:
        return existing
    donor = Donor(name=(name or "").strip() or "Unknown", email=normalized, phone=phone, donor_type=donor_type)
    db.session.add(donor)
    db.session.flush()
    return donor


def donor_stats(donor):
    """Real, derived-at-read-time numbers — nothing stored, nothing that
    can drift out of sync with the donations that actually happened.
    Counts every linked donation regardless of status (a donor's profile
    should show their full history, including a Pending one) except for
    lifetime_amount, which only counts real received value — same
    DONATION_COUNTED_STATUSES rule campaign progress and reports use."""
    donations = Donation.query.filter_by(donor_id=donor.id).order_by(Donation.created_at.desc()).all()
    counted = [d for d in donations if d.status in DONATION_COUNTED_STATUSES and d.amount is not None]
    lifetime_amount = sum(d.amount for d in counted)
    campaign_names = sorted({d.campaign_obj.name if d.campaign_obj else d.campaign for d in donations if d.campaign_obj or d.campaign})
    return {
        "lifetime_amount": lifetime_amount,
        "donation_count": len(donations),
        "most_recent_donation_at": donations[0].created_at if donations else None,
        "campaigns_supported": campaign_names,
        "donations": donations,
    }
