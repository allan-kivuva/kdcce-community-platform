from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..documents.service import DocumentError, document_file_path, save_document
from ..extensions import db
from ..models import Campaign, Expense, Program, utcnow
from ..utils import get_or_404, validation_error_response
from .schemas import ExpenseMetaSchema, ExpenseUpdateSchema

bp = Blueprint("expenses", __name__, url_prefix="/api/expenses")

meta_schema = ExpenseMetaSchema()
update_schema = ExpenseUpdateSchema()

_SNAPSHOT_FIELDS = ("amount", "category", "program_id", "campaign_id", "expense_date", "vendor_name", "status")


def _snapshot(expense):
    snapshot = {}
    for field in _SNAPSHOT_FIELDS:
        value = getattr(expense, field)
        if field == "amount":
            value = float(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        snapshot[field] = value
    return snapshot


def _program_or_400(program_id):
    if db.session.get(Program, program_id) is None:
        return jsonify(error="Validation failed", details={"program_id": ["Program not found"]}), 400
    return None


def _campaign_or_400(campaign_id):
    if db.session.get(Campaign, campaign_id) is None:
        return jsonify(error="Validation failed", details={"campaign_id": ["Campaign not found"]}), 400
    return None


@bp.get("")
@roles_required("admin", "staff")
def list_expenses():
    query = Expense.query
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    program_id = request.args.get("program_id", type=int)
    if program_id is not None:
        query = query.filter_by(program_id=program_id)
    category = request.args.get("category")
    if category:
        query = query.filter_by(category=category)
    expenses = query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()
    return jsonify(expenses=[e.to_dict() for e in expenses]), 200


@bp.post("")
@roles_required("admin", "staff")
def create_expense():
    """Multipart, not JSON — a receipt file is optional but this keeps
    one request/one endpoint for "record an expense (with or without a
    receipt)" rather than a create-then-attach two-step. Reuses
    documents/service.py's exact upload mechanism (magic-byte sniffing,
    size limits, safe storage keys) for the receipt — no second upload
    system."""
    try:
        data = meta_schema.load(request.form.to_dict())
    except ValidationError as err:
        return validation_error_response(err)
    if data.get("program_id") is not None:
        invalid = _program_or_400(data["program_id"])
        if invalid:
            return invalid
    if data.get("campaign_id") is not None:
        invalid = _campaign_or_400(data["campaign_id"])
        if invalid:
            return invalid

    identity = int(get_jwt_identity())
    expense = Expense(**data, recorded_by_id=identity, status="Recorded")
    db.session.add(expense)
    db.session.flush()

    if request.files.get("file"):
        try:
            document = save_document(
                "expense", expense.id, identity, request.files.get("file"),
                document_type="Receipt", title=f"Receipt — {expense.category} ({expense.expense_date.isoformat()})",
                visibility="Admin", auto_verified=True,
            )
        except DocumentError as err:
            db.session.rollback()
            return jsonify(error="Validation failed", details={"file": [err.message]}), 400
        expense.document_id = document.id

    log_action(identity, "create", "expense", expense.id, after=_snapshot(expense))
    db.session.commit()
    return jsonify(expense=expense.to_dict()), 201


@bp.get("/<int:expense_id>")
@roles_required("admin", "staff")
def get_expense(expense_id):
    expense = get_or_404(Expense, expense_id)
    return jsonify(expense=expense.to_dict()), 200


@bp.get("/<int:expense_id>/receipt")
@roles_required("admin", "staff")
def get_expense_receipt(expense_id):
    expense = get_or_404(Expense, expense_id)
    if expense.document is None:
        return jsonify(error="No receipt attached to this expense"), 404
    return send_file(document_file_path(expense.document), mimetype=expense.document.mime_type, download_name=expense.document.original_filename)


@bp.patch("/<int:expense_id>")
@jwt_required()
def update_expense(expense_id):
    expense = get_or_404(Expense, expense_id)
    role = get_jwt().get("role")
    if role not in ("admin", "staff"):
        return jsonify(error="Forbidden"), 403

    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "status" in data and data["status"] in ("Approved", "Rejected", "Voided") and role != "admin":
        # Staff can record and edit the descriptive fields; only admin
        # signs off on approval/rejection/voiding — same precedent as
        # AssignmentReview being admin-only while its module otherwise
        # uses the ("admin", "staff") pair everywhere else.
        return jsonify(error="Forbidden"), 403

    if "program_id" in data and data["program_id"] is not None:
        invalid = _program_or_400(data["program_id"])
        if invalid:
            return invalid
    if "campaign_id" in data and data["campaign_id"] is not None:
        invalid = _campaign_or_400(data["campaign_id"])
        if invalid:
            return invalid

    before = _snapshot(expense)
    for field, value in data.items():
        setattr(expense, field, value)
    if "status" in data and data["status"] in ("Approved", "Rejected"):
        expense.approved_by_id = int(get_jwt_identity())
        expense.approved_at = utcnow()
    db.session.flush()
    action = "status_change" if "status" in data else "update"
    log_action(int(get_jwt_identity()), action, "expense", expense.id, before=before, after=_snapshot(expense))
    db.session.commit()
    return jsonify(expense=expense.to_dict()), 200
