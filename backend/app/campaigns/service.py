from decimal import Decimal

from ..extensions import db
from ..models import Campaign, Donation, DONATION_COUNTED_STATUSES

PUBLIC_STATUSES = ("Active", "Completed")


def find_campaign_by_exact_name(name):
    """Used at donation-creation time (both the public and staff forms)
    to auto-populate campaign_id going forward, without touching the
    free-text `campaign` field at all. Exact, case-insensitive match
    only — the same conservative rule link_matching_donations uses for
    historical rows, applied at the moment of creation instead."""
    if not name:
        return None
    return Campaign.query.filter(db.func.lower(Campaign.name) == name.strip().lower()).first()


def campaign_progress(campaign, recent_limit=5):
    """Derived entirely from real Donation rows at read time — nothing
    stored, nothing that can drift. Only counts donations whose status
    represents received value (DONATION_COUNTED_STATUSES — Paid/
    Received, never Pending/cancelled/etc.), matching the same rule
    the donations report uses. See models.py's note on Donation.status:
    "Paid"/"Received" are staff-confirmed workflow labels, not verified
    payments — the honest caveat is documented there and in this phase's
    final report, not hidden."""
    donations = (
        Donation.query.filter_by(campaign_id=campaign.id)
        .filter(Donation.status.in_(DONATION_COUNTED_STATUSES))
        .order_by(Donation.created_at.desc())
        .all()
    )
    raised = sum((d.amount for d in donations if d.amount is not None), Decimal("0"))
    goal = campaign.goal_amount
    remaining = goal - raised
    percent = round(float(raised / goal) * 100, 1) if goal and goal > 0 else None
    return {
        "goal_amount": float(goal),
        "raised_amount": float(raised),
        "remaining_amount": float(remaining),
        "percent_achieved": percent,
        "donation_count": len(donations),
        "recent_donations": [d.to_dict() for d in donations[:recent_limit]],
    }


def link_matching_donations(campaign):
    """Admin-triggered, exact-match-only linking of pre-existing free-
    text donations to this campaign — the safe alternative to silently
    auto-linking at migration time (there IS no Campaign record yet when
    old donations were created, so nothing to match against then; this
    is for later, once staff have created the real Campaign a batch of
    old donations' free-text `campaign` field was describing all along).
    Case-insensitive exact match only — never a fuzzy/partial match that
    could misattribute a donation to the wrong campaign."""
    matched = (
        Donation.query.filter(Donation.campaign_id.is_(None))
        .filter(db.func.lower(Donation.campaign) == campaign.name.strip().lower())
        .all()
    )
    for donation in matched:
        donation.campaign_id = campaign.id
    return len(matched)
