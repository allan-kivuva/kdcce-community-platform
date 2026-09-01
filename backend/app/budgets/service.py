from ..extensions import db
from ..models import EXPENSE_COUNTED_STATUSES, Expense

# Informational thresholds only (never blocking) — see budgets/routes.py.
WARNING_THRESHOLD = 75
ALERT_THRESHOLD = 90


def budget_spent(budget):
    """Real spend for this budget's program, scoped to its period if one
    is set — derived at read time from Expense rows, never stored.
    Only counts Recorded/Approved expenses (EXPENSE_COUNTED_STATUSES);
    Rejected/Voided expenses never happened as far as the budget is
    concerned."""
    query = Expense.query.filter(Expense.program_id == budget.program_id, Expense.status.in_(EXPENSE_COUNTED_STATUSES))
    if budget.period_start:
        query = query.filter(Expense.expense_date >= budget.period_start)
    if budget.period_end:
        query = query.filter(Expense.expense_date <= budget.period_end)
    total = query.with_entities(db.func.coalesce(db.func.sum(Expense.amount), 0)).scalar()
    return float(total)


def budget_warning_level(allocated_amount, spent):
    """None | "warning" (>=75%) | "alert" (>=90%) | "exceeded" (>100%) —
    purely informational, per this phase's "warnings should be
    informational unless policy explicitly requires blocking" rule; no
    endpoint in this app refuses to record an expense because of one."""
    if allocated_amount <= 0:
        return None
    percent = (spent / allocated_amount) * 100
    if percent > 100:
        return "exceeded"
    if percent >= ALERT_THRESHOLD:
        return "alert"
    if percent >= WARNING_THRESHOLD:
        return "warning"
    return None
