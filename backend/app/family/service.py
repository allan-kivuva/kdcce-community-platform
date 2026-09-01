from ..consent.service import is_granted
from ..models import FamilyMemberAccess


def authorized_access(user_id, elderly_member_id):
    """The single choke point every family/routes.py endpoint calls
    before touching any elderly-member data. Returns the
    FamilyMemberAccess row only if this exact (user, member) pair has
    Active status AND "Family Portal Access" consent is currently
    granted for that member — both re-checked fresh on every call,
    never cached, so a revocation or a consent withdrawal takes effect
    on the very next request. Returns None otherwise; every caller
    treats None identically whether the member doesn't exist or simply
    isn't authorized — never distinguishing the two in the response."""
    access = FamilyMemberAccess.query.filter_by(
        user_id=user_id, elderly_member_id=elderly_member_id, access_status="Active",
    ).first()
    if access is None:
        return None
    if not is_granted(elderly_member_id, "Family Portal Access"):
        return None
    return access


def active_accesses_for_user(user_id):
    """Every member this family user currently has live, consent-backed
    access to — the exact set GET /api/family/members returns."""
    rows = FamilyMemberAccess.query.filter_by(user_id=user_id, access_status="Active").all()
    return [row for row in rows if is_granted(row.elderly_member_id, "Family Portal Access")]
