"""Shared aggregation behind GET /api/reports/operational-summary and
the `generate-operational-report` CLI command (see cli.py) — one
function, two callers, so the on-demand API result and the cron-able
CLI snapshot can never drift apart. Deliberately a compact cross-module
KPI set, not a re-implementation of every existing per-module report
already under this same blueprint."""

from datetime import timedelta

from ..extensions import db
from ..models import (
    DONATION_COUNTED_STATUSES, ActivityParticipant, Donation, EXPENSE_COUNTED_STATUSES, Expense,
    HomeVisit, Incident, InventoryItem, MealAttendance, VolunteerHours, utcnow,
)


def operational_summary():
    now = utcnow()
    month_start = now.date().replace(day=1)
    week_ahead = now + timedelta(days=7)

    unresolved_incidents = Incident.query.filter(Incident.status.in_(("Open", "Under Review"))).count()
    upcoming_visits_7d = HomeVisit.query.filter(
        HomeVisit.status.in_(("Pending", "Assigned", "Accepted", "Scheduled")),
        HomeVisit.scheduled_at.isnot(None), HomeVisit.scheduled_at <= week_ahead,
    ).count()
    approved_minutes_this_month = db.session.query(db.func.coalesce(db.func.sum(VolunteerHours.duration_minutes), 0)).filter(
        VolunteerHours.status == "Approved", VolunteerHours.date >= month_start,
    ).scalar()
    program_attendance_this_month = ActivityParticipant.query.filter(
        ActivityParticipant.status == "Attended", ActivityParticipant.updated_at >= month_start,
    ).count()
    donations_total_this_month = db.session.query(db.func.coalesce(db.func.sum(Donation.amount), 0)).filter(
        Donation.status.in_(DONATION_COUNTED_STATUSES), Donation.created_at >= month_start,
    ).scalar()
    expenses_total_this_month = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0)).filter(
        Expense.status.in_(EXPENSE_COUNTED_STATUSES), Expense.expense_date >= month_start,
    ).scalar()
    low_stock_items = InventoryItem.query.filter(InventoryItem.current_stock <= InventoryItem.minimum_stock).count()
    meals_served_this_month = MealAttendance.query.filter(MealAttendance.created_at >= month_start).count()

    return {
        "generated_at": now.isoformat(),
        "period_start": month_start.isoformat(),
        "unresolved_incidents": unresolved_incidents,
        "upcoming_visits_7d": upcoming_visits_7d,
        "approved_volunteer_hours_this_month": round(float(approved_minutes_this_month) / 60, 1),
        "program_attendance_this_month": program_attendance_this_month,
        "donations_total_this_month": float(donations_total_this_month),
        "expenses_total_this_month": float(expenses_total_this_month),
        "low_stock_item_count": low_stock_items,
        "meals_served_this_month": meals_served_this_month,
    }
