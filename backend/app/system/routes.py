import os
import subprocess
from datetime import timedelta

from flask import Blueprint, jsonify

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import AuditLog, LoginHistory, User, UserSession, utcnow

bp = Blueprint("system", __name__, url_prefix="/api/system")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Critical-by-convention: any AuditLog action name that represents an
# account/access-control change worth an admin's immediate attention on
# the security overview page, as opposed to routine record edits.
CRITICAL_AUDIT_ACTIONS = (
    "delete", "restore", "role_change", "deactivate", "disable",
    "revoke", "revoke_others", "revoke_all", "recovery_code_used",
)


def _git_commit():
    # Best-effort only — never exposes anything beyond a short commit
    # hash (no paths, no branch name, no remote URL), and never raises:
    # a dev checkout with no .git, or git missing entirely, just means
    # this comes back None.
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2, cwd=_REPO_ROOT,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


@bp.get("/security-overview")
@roles_required("admin")
def security_overview():
    db_connected = True
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        db_connected = False

    since = utcnow() - timedelta(hours=24)
    recent_failed_logins = (
        LoginHistory.query.filter(LoginHistory.success.is_(False), LoginHistory.created_at >= since)
        .order_by(LoginHistory.created_at.desc())
        .limit(10)
        .all()
    )
    active_session_count = UserSession.query.filter(
        UserSession.revoked_at.is_(None), UserSession.expires_at > utcnow()
    ).count()
    recent_critical_events = (
        AuditLog.query.filter(AuditLog.action.in_(CRITICAL_AUDIT_ACTIONS))
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    disabled_account_count = User.query.filter(User.active.is_(False), User.deleted_at.is_(None)).count()
    admins = User.query.filter_by(role="admin").filter(User.deleted_at.is_(None)).all()
    admin_2fa_enabled = sum(1 for admin in admins if admin.totp_enabled)

    return jsonify(
        api_status="ok",
        db_connected=db_connected,
        recent_failed_logins=[entry.to_dict() for entry in recent_failed_logins],
        active_session_count=active_session_count,
        recent_critical_events=[event.to_dict() for event in recent_critical_events],
        disabled_account_count=disabled_account_count,
        admin_2fa_coverage={"enabled": admin_2fa_enabled, "total": len(admins)},
        commit=_git_commit(),
    ), 200
