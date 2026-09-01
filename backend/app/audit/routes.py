from flask import Blueprint, jsonify, request

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import AuditLog
from ..utils import ReportFilterError, get_or_404, parse_date_range

bp = Blueprint("audit", __name__, url_prefix="/api/audit-logs")


@bp.get("")
@roles_required("admin")
def list_audit_logs():
    """Admin-only — this is the org's own change history across every
    sensitive action the platform tracks (financial records, user/role
    changes, session revocation, 2FA, verification/rejection decisions,
    ...), not something staff-level access extends to."""
    query = AuditLog.query

    resource_type = request.args.get("resource_type")
    if resource_type:
        query = query.filter_by(resource_type=resource_type)
    resource_id = request.args.get("resource_id", type=int)
    if resource_id is not None:
        query = query.filter_by(resource_id=resource_id)
    action = request.args.get("action")
    if action:
        query = query.filter_by(action=action)
    actor_id = request.args.get("actor_id", type=int)
    if actor_id is not None:
        query = query.filter_by(actor_id=actor_id)

    try:
        date_from, date_to = parse_date_range(request.args)
    except ReportFilterError as err:
        return jsonify(error="Validation failed", details={err.field: [err.message]}), 400
    if date_from:
        query = query.filter(db.func.date(AuditLog.created_at) >= date_from.isoformat())
    if date_to:
        query = query.filter(db.func.date(AuditLog.created_at) <= date_to.isoformat())

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    query = query.order_by(AuditLog.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        audit_logs=[a.to_dict() for a in items],
        pagination={"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page if per_page else 0},
    ), 200


@bp.get("/<int:log_id>")
@roles_required("admin")
def get_audit_log(log_id):
    entry = get_or_404(AuditLog, log_id)
    return jsonify(audit_log=entry.to_dict()), 200
