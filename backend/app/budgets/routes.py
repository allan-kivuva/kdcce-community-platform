from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Budget, Program
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import BudgetCreateSchema, BudgetUpdateSchema

bp = Blueprint("budgets", __name__, url_prefix="/api/budgets")

create_schema = BudgetCreateSchema()
update_schema = BudgetUpdateSchema()

_SNAPSHOT_FIELDS = ("program_id", "period_start", "period_end", "allocated_amount", "notes")


def _snapshot(budget):
    snapshot = {}
    for field in _SNAPSHOT_FIELDS:
        value = getattr(budget, field)
        if field == "allocated_amount":
            value = float(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        snapshot[field] = value
    return snapshot


def _budget_dict(budget):
    spent = service.budget_spent(budget)
    data = budget.to_dict(spent=spent)
    data["warning_level"] = service.budget_warning_level(float(budget.allocated_amount), spent)
    return data


@bp.get("")
@roles_required("admin", "staff")
def list_budgets():
    query = Budget.query
    program_id = request.args.get("program_id", type=int)
    if program_id is not None:
        query = query.filter_by(program_id=program_id)
    budgets = query.order_by(Budget.created_at.desc()).all()
    return jsonify(budgets=[_budget_dict(b) for b in budgets]), 200


@bp.post("")
@roles_required("admin", "staff")
def create_budget():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)
    if db.session.get(Program, data["program_id"]) is None:
        return jsonify(error="Validation failed", details={"program_id": ["Program not found"]}), 400

    budget = Budget(**data, created_by_id=int(get_jwt_identity()))
    db.session.add(budget)
    db.session.flush()
    log_action(int(get_jwt_identity()), "create", "budget", budget.id, after=_snapshot(budget))
    db.session.commit()
    return jsonify(budget=_budget_dict(budget)), 201


@bp.get("/<int:budget_id>")
@roles_required("admin", "staff")
def get_budget(budget_id):
    budget = get_or_404(Budget, budget_id)
    return jsonify(budget=_budget_dict(budget)), 200


@bp.patch("/<int:budget_id>")
@roles_required("admin", "staff")
def update_budget(budget_id):
    budget = get_or_404(Budget, budget_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    before = _snapshot(budget)
    for field, value in data.items():
        setattr(budget, field, value)
    db.session.flush()
    log_action(int(get_jwt_identity()), "update", "budget", budget.id, before=before, after=_snapshot(budget))
    db.session.commit()
    return jsonify(budget=_budget_dict(budget)), 200
