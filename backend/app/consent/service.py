from ..extensions import db
from ..models import Consent, utcnow


def current_consent(elderly_member_id, consent_type):
    """The newest Consent row for this (member, type) — the live status
    every consumer must check, since a withdrawal is a new row, not an
    edit to an old one. Returns None if consent of this type has never
    been recorded at all (treated as "not granted" by every caller)."""
    return (
        Consent.query.filter_by(elderly_member_id=elderly_member_id, consent_type=consent_type)
        .order_by(Consent.created_at.desc())
        .first()
    )


def is_granted(elderly_member_id, consent_type):
    consent = current_consent(elderly_member_id, consent_type)
    return consent is not None and consent.status == "Granted"


def record_consent(elderly_member_id, consent_type, status, recorded_by_id, notes=None, document_id=None):
    """Always INSERTs a new row — see the Consent model docstring for why
    this is append-only rather than an update. Does not commit; the
    caller's route commits (and audits) in the same transaction."""
    now = utcnow()
    consent = Consent(
        elderly_member_id=elderly_member_id,
        consent_type=consent_type,
        status=status,
        granted_at=now if status == "Granted" else None,
        withdrawn_at=now if status == "Withdrawn" else None,
        recorded_by_id=recorded_by_id,
        notes=notes,
        document_id=document_id,
    )
    db.session.add(consent)
    return consent
