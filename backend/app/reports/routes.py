from flask import Blueprint, jsonify, request

from ..auth.decorators import roles_required
from ..extensions import db
from ..budgets.service import budget_spent, budget_warning_level
from . import service as reports_service
from ..models import (
    Activity, ActivityParticipant, AssistanceRequest, Attendance, Budget, Campaign, Donation,
    DONATION_COUNTED_STATUSES, Donor, ElderlyMember, EXPENSE_COUNTED_STATUSES, Expense,
    FollowUp, HealthRecord, HomeVisit, Incident, InventoryItem, Meal, MealAttendance, Medication,
    MedicationAdministration, Program, StockMovement, User, VolunteerProfile,
)
from ..utils import ReportFilterError, csv_response, parse_date_range

bp = Blueprint("reports", __name__, url_prefix="/api/reports")

# Every report is admin/staff only, no exceptions — each one aggregates
# elderly-adjacent data that volunteers have no access to at the module
# level, and a report layer must not become a backdoor around that.
_REPORT_ROLES = ("admin", "staff")


def _bad_filter(err):
    return jsonify(error="Validation failed", details={err.field: [err.message]}), 400


def _parse_dates():
    """Returns (date_from, date_to, error_response_or_None)."""
    try:
        return (*parse_date_range(request.args), None)
    except ReportFilterError as err:
        return None, None, _bad_filter(err)


def _count_by(query, column):
    """GROUP BY count as one aggregate query — never loads matching rows
    into Python just to tally them there."""
    rows = query.with_entities(column, db.func.count()).group_by(column).all()
    return {(key if key is not None else "Not noted"): count for key, count in rows}


# ---------- Attendance ----------

@bp.get("/attendance")
@roles_required(*_REPORT_ROLES)
def attendance_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    opa_id = request.args.get("opa_id", type=int)

    members = ElderlyMember.query
    if opa_id:
        members = members.filter(ElderlyMember.opa_id == opa_id)
    registered_count = members.count()

    records = Attendance.query
    if opa_id:
        records = records.join(ElderlyMember, Attendance.elderly_member_id == ElderlyMember.id).filter(ElderlyMember.opa_id == opa_id)
    if date_from:
        records = records.filter(Attendance.attendance_date >= date_from)
    if date_to:
        records = records.filter(Attendance.attendance_date <= date_to)

    total_records = records.count()
    checked_out = records.filter(Attendance.check_out_at.isnot(None)).count()

    by_day_rows = (
        records.with_entities(Attendance.attendance_date, db.func.count())
        .group_by(Attendance.attendance_date).order_by(Attendance.attendance_date.asc()).all()
    )
    by_day = [{"date": d.isoformat(), "count": c} for d, c in by_day_rows]
    counts = [c for _, c in by_day_rows]
    active_days = len(counts) or 1
    distinct_member_days = records.with_entities(Attendance.elderly_member_id, Attendance.attendance_date).distinct().count()

    return jsonify(report={
        "registered_count": registered_count,
        "total_records": total_records,
        "checked_out": checked_out,
        "still_checked_in": total_records - checked_out,
        "by_day": by_day,
        "average_daily": round(sum(counts) / active_days, 1) if counts else 0,
        "highest_day": max(counts) if counts else 0,
        "lowest_day": min(counts) if counts else 0,
        # Distinct (member, day) pairs against the registered roster and the
        # days that actually had any attendance — not calendar days, so a
        # centre closed on Sundays isn't penalized for being closed.
        "attendance_percentage": round(distinct_member_days / (registered_count * active_days) * 100, 1) if registered_count else 0,
    }), 200


@bp.get("/attendance/export.csv")
@roles_required(*_REPORT_ROLES)
def attendance_report_csv():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    opa_id = request.args.get("opa_id", type=int)

    records = Attendance.query
    if opa_id:
        records = records.join(ElderlyMember, Attendance.elderly_member_id == ElderlyMember.id).filter(ElderlyMember.opa_id == opa_id)
    if date_from:
        records = records.filter(Attendance.attendance_date >= date_from)
    if date_to:
        records = records.filter(Attendance.attendance_date <= date_to)

    rows = records.with_entities(Attendance.attendance_date, db.func.count()).group_by(Attendance.attendance_date).order_by(Attendance.attendance_date.asc()).all()
    return csv_response("attendance_report.csv", ["Date", "Attendance Count"], [[d.isoformat(), c] for d, c in rows])


# ---------- Health & wellness ----------

@bp.get("/health")
@roles_required(*_REPORT_ROLES)
def health_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    opa_id = request.args.get("opa_id", type=int)

    records = HealthRecord.query
    if opa_id:
        records = records.join(ElderlyMember, HealthRecord.elderly_member_id == ElderlyMember.id).filter(ElderlyMember.opa_id == opa_id)
    if date_from:
        records = records.filter(db.func.date(HealthRecord.recorded_at) >= date_from.isoformat())
    if date_to:
        records = records.filter(db.func.date(HealthRecord.recorded_at) <= date_to.isoformat())

    medications = Medication.query
    if opa_id:
        medications = medications.join(ElderlyMember, Medication.elderly_member_id == ElderlyMember.id).filter(ElderlyMember.opa_id == opa_id)
    if date_from:
        medications = medications.filter(Medication.start_date >= date_from)
    if date_to:
        medications = medications.filter(Medication.start_date <= date_to)

    administrations = MedicationAdministration.query
    if date_from:
        administrations = administrations.filter(db.func.date(MedicationAdministration.administered_at) >= date_from.isoformat())
    if date_to:
        administrations = administrations.filter(db.func.date(MedicationAdministration.administered_at) <= date_to.isoformat())

    return jsonify(report={
        "health_checks_completed": records.count(),
        "follow_ups_required": records.filter(HealthRecord.follow_up_required.is_(True)).count(),
        # A plain tally of recorded wellbeing values, not a diagnosis or
        # clinical trend judgment — this is administrative reporting.
        "wellness_trend": _count_by(records, HealthRecord.wellbeing),
        "medications_started": medications.count(),
        "medication_administration": _count_by(administrations, MedicationAdministration.status),
        # Not available: no clinic/medical-visit module exists yet.
        "clinic_visits": None,
    }), 200


# ---------- Home visits ----------

@bp.get("/home-visits")
@roles_required(*_REPORT_ROLES)
def home_visits_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    opa_id = request.args.get("opa_id", type=int)
    volunteer_id = request.args.get("volunteer_id", type=int)

    visits = HomeVisit.query
    if opa_id:
        visits = visits.join(ElderlyMember, HomeVisit.elderly_member_id == ElderlyMember.id).filter(ElderlyMember.opa_id == opa_id)
    if volunteer_id:
        visits = visits.filter(HomeVisit.assigned_to_id == volunteer_id)
    if date_from:
        visits = visits.filter(db.func.date(HomeVisit.created_at) >= date_from.isoformat())
    if date_to:
        visits = visits.filter(db.func.date(HomeVisit.created_at) <= date_to.isoformat())

    by_volunteer_rows = (
        visits.join(User, HomeVisit.assigned_to_id == User.id)
        .with_entities(User.name, db.func.count()).group_by(User.name).all()
    )

    return jsonify(report={
        "total": visits.count(),
        "by_status": _count_by(visits, HomeVisit.status),
        "follow_up_required": visits.filter(HomeVisit.follow_up_required.is_(True)).count(),
        "by_volunteer": {name: count for name, count in by_volunteer_rows},
    }), 200


@bp.get("/home-visits/export.csv")
@roles_required(*_REPORT_ROLES)
def home_visits_report_csv():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    opa_id = request.args.get("opa_id", type=int)

    visits = HomeVisit.query
    if opa_id:
        visits = visits.join(ElderlyMember, HomeVisit.elderly_member_id == ElderlyMember.id).filter(ElderlyMember.opa_id == opa_id)
    if date_from:
        visits = visits.filter(db.func.date(HomeVisit.created_at) >= date_from.isoformat())
    if date_to:
        visits = visits.filter(db.func.date(HomeVisit.created_at) <= date_to.isoformat())

    rows = [
        [v.elderly_member.full_name, v.status, v.priority, v.assigned_to.name if v.assigned_to else "", v.created_at.isoformat()]
        for v in visits.order_by(HomeVisit.created_at.desc()).all()
    ]
    return csv_response("home_visits_report.csv", ["Elderly Member", "Status", "Priority", "Assigned To", "Created"], rows)


# ---------- Volunteers ----------

@bp.get("/volunteers")
@roles_required(*_REPORT_ROLES)
def volunteers_report():
    status_counts = _count_by(VolunteerProfile.query, VolunteerProfile.status)

    verified = VolunteerProfile.query.filter_by(status="Verified").all()
    workload = []
    for profile in verified:
        visits = HomeVisit.query.filter_by(assigned_to_id=profile.user_id)
        requests_ = AssistanceRequest.query.filter_by(assigned_to_id=profile.user_id)

        visits_total = visits.count()
        requests_total = requests_.count()
        visits_completed = visits.filter_by(status="Completed").count()
        requests_completed = requests_.filter_by(status="Completed").count()
        visits_cancelled = visits.filter_by(status="Cancelled").count()
        requests_cancelled = requests_.filter_by(status="Cancelled").count()
        total = visits_total + requests_total
        completed = visits_completed + requests_completed
        cancelled = visits_cancelled + requests_cancelled
        active = (
            visits.filter(HomeVisit.status.in_(("Assigned", "Scheduled", "In Progress"))).count()
            + requests_.filter(AssistanceRequest.status.in_(("Assigned", "Accepted", "In Progress"))).count()
        )

        assigned_elderly_count = (
            db.session.query(db.func.count(db.distinct(HomeVisit.elderly_member_id)))
            .filter(HomeVisit.assigned_to_id == profile.user_id, HomeVisit.status.in_(("Assigned", "Scheduled", "In Progress")))
            .scalar()
        )

        workload.append({
            "user_id": profile.user_id,
            "name": profile.user.name,
            "home_visits_total": visits_total,
            "home_visits_completed": visits_completed,
            "assistance_requests_total": requests_total,
            "assistance_requests_completed": requests_completed,
            "active_assignments": active,
            "pending_assignments": max(total - completed - cancelled, 0),
            "cancelled_assignments": cancelled,
            "completion_rate": round(completed / total * 100, 1) if total else 0.0,
            "assigned_elderly_count": assigned_elderly_count,
            "follow_ups_completed": FollowUp.query.filter_by(assigned_to_id=profile.user_id, status="Completed").count(),
        })

    return jsonify(report={
        # No "volunteer hours" field: nothing in this system records
        # duration/time-on-task, so a number here would be fabricated,
        # not measured — see docs/api/reports.md.
        "by_status": status_counts,
        "active_volunteers": status_counts.get("Verified", 0),
        "workload": workload,
    }), 200


# ---------- Feeding ----------

@bp.get("/feeding")
@roles_required(*_REPORT_ROLES)
def feeding_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err

    meals = Meal.query
    if date_from:
        meals = meals.filter(Meal.meal_date >= date_from)
    if date_to:
        meals = meals.filter(Meal.meal_date <= date_to)

    attendance = MealAttendance.query.join(Meal, MealAttendance.meal_id == Meal.id)
    if date_from:
        attendance = attendance.filter(Meal.meal_date >= date_from)
    if date_to:
        attendance = attendance.filter(Meal.meal_date <= date_to)

    by_date_rows = (
        attendance.with_entities(Meal.meal_date, db.func.count())
        .group_by(Meal.meal_date).order_by(Meal.meal_date.asc()).all()
    )
    dietary_flagged = (
        attendance.join(ElderlyMember, MealAttendance.elderly_member_id == ElderlyMember.id)
        .filter(db.or_(ElderlyMember.allergies.isnot(None), ElderlyMember.dietary_requirements.isnot(None)))
        .with_entities(MealAttendance.elderly_member_id).distinct().count()
    )

    return jsonify(report={
        "meals_planned": meals.count(),
        "meals_served": attendance.count(),
        "meals_by_date": [{"date": d.isoformat(), "attendee_count": c} for d, c in by_date_rows],
        "dietary_flagged_attendees": dietary_flagged,
    }), 200


# ---------- Inventory ----------

@bp.get("/inventory")
@roles_required(*_REPORT_ROLES)
def inventory_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    category = request.args.get("category")

    items = InventoryItem.query
    if category:
        items = items.filter(InventoryItem.category == category)
    all_items = [i.to_dict() for i in items.order_by(InventoryItem.name.asc()).all()]

    movements = StockMovement.query
    if category:
        movements = movements.join(InventoryItem, StockMovement.item_id == InventoryItem.id).filter(InventoryItem.category == category)
    if date_from:
        movements = movements.filter(db.func.date(StockMovement.created_at) >= date_from.isoformat())
    if date_to:
        movements = movements.filter(db.func.date(StockMovement.created_at) <= date_to.isoformat())

    totals = movements.with_entities(StockMovement.movement_type, db.func.sum(StockMovement.quantity)).group_by(StockMovement.movement_type).all()
    totals_by_type = {t: float(q) for t, q in totals}

    by_date_rows = (
        movements.with_entities(db.func.date(StockMovement.created_at), StockMovement.movement_type, db.func.sum(StockMovement.quantity))
        .group_by(db.func.date(StockMovement.created_at), StockMovement.movement_type)
        .order_by(db.func.date(StockMovement.created_at).asc()).all()
    )
    by_date = {}
    for d, movement_type, qty in by_date_rows:
        by_date.setdefault(d, {"date": d, "in_total": 0, "out_total": 0})
        by_date[d]["in_total" if movement_type == "In" else "out_total"] = float(qty)

    return jsonify(report={
        # The ledger (StockMovement) stays the only source of the balance —
        # current_stock here is read straight off InventoryItem.to_dict(),
        # never recomputed independently.
        "items": all_items,
        "low_stock_items": [i for i in all_items if i["low_stock"]],
        "stock_in_total": totals_by_type.get("In", 0),
        "stock_out_total": totals_by_type.get("Out", 0),
        "movements_by_date": list(by_date.values()),
        "donation_linked_movements": movements.filter(StockMovement.donation_id.isnot(None)).count(),
    }), 200


@bp.get("/inventory/export.csv")
@roles_required(*_REPORT_ROLES)
def inventory_report_csv():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    category = request.args.get("category")

    movements = StockMovement.query
    if category:
        movements = movements.join(InventoryItem, StockMovement.item_id == InventoryItem.id).filter(InventoryItem.category == category)
    if date_from:
        movements = movements.filter(db.func.date(StockMovement.created_at) >= date_from.isoformat())
    if date_to:
        movements = movements.filter(db.func.date(StockMovement.created_at) <= date_to.isoformat())

    rows = [
        [m.item.name, m.movement_type, float(m.quantity), m.reason or "", m.recorded_by.name, m.created_at.isoformat()]
        for m in movements.order_by(StockMovement.created_at.desc()).all()
    ]
    return csv_response("inventory_movements_report.csv", ["Item", "Type", "Quantity", "Reason", "Recorded By", "Date"], rows)


# ---------- Donations ----------

@bp.get("/donations")
@roles_required(*_REPORT_ROLES)
def donations_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    donation_type = request.args.get("donation_type")

    donations = Donation.query
    if donation_type:
        donations = donations.filter(Donation.donation_type == donation_type)
    if date_from:
        donations = donations.filter(db.func.date(Donation.created_at) >= date_from.isoformat())
    if date_to:
        donations = donations.filter(db.func.date(Donation.created_at) <= date_to.isoformat())

    cash_total = donations.filter(Donation.donation_type == "Cash").with_entities(db.func.coalesce(db.func.sum(Donation.amount), 0)).scalar()
    by_date_rows = (
        donations.with_entities(db.func.date(Donation.created_at), db.func.count())
        .group_by(db.func.date(Donation.created_at)).order_by(db.func.date(Donation.created_at).asc()).all()
    )
    # Phase 6: counted (Paid/Received) donations grouped by free-text
    # campaign label — deliberately the text field, not campaign_id, so
    # this still reflects every donation including ones from before any
    # Campaign record existed to link to.
    by_campaign_rows = (
        donations.filter(Donation.status.in_(DONATION_COUNTED_STATUSES), Donation.campaign.isnot(None))
        .with_entities(Donation.campaign, db.func.coalesce(db.func.sum(Donation.amount), 0), db.func.count())
        .group_by(Donation.campaign).order_by(db.func.coalesce(db.func.sum(Donation.amount), 0).desc()).all()
    )

    return jsonify(report={
        "total_count": donations.count(),
        "by_type": _count_by(donations, Donation.donation_type),
        "cash_total": float(cash_total),
        "by_date": [{"date": d, "count": c} for d, c in by_date_rows],
        "by_campaign": [{"campaign": c, "amount": float(a), "count": n} for c, a, n in by_campaign_rows],
    }), 200


@bp.get("/donations/history")
@roles_required(*_REPORT_ROLES)
def donations_history():
    """Paginated donation history for the report view — the existing
    GET /api/donations (donations module) already lists everything
    unpaginated for the admin manager UI; this is the filtered,
    paginated variant reports need for a potentially large date range."""
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    donation_type = request.args.get("donation_type")
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)

    donations = Donation.query
    if donation_type:
        donations = donations.filter(Donation.donation_type == donation_type)
    if date_from:
        donations = donations.filter(db.func.date(Donation.created_at) >= date_from.isoformat())
    if date_to:
        donations = donations.filter(db.func.date(Donation.created_at) <= date_to.isoformat())

    donations = donations.order_by(Donation.created_at.desc())
    total = donations.count()
    page_items = donations.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify(
        donations=[d.to_dict() for d in page_items],
        pagination={"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page if per_page else 0},
    ), 200


# ---------- Campaigns (Phase 6) ----------

@bp.get("/campaigns")
@roles_required(*_REPORT_ROLES)
def campaigns_report():
    campaigns = Campaign.query.all()
    rows = []
    for c in campaigns:
        counted = Donation.query.filter_by(campaign_id=c.id).filter(Donation.status.in_(DONATION_COUNTED_STATUSES)).all()
        raised = sum((d.amount for d in counted if d.amount is not None), 0)
        rows.append({
            "id": c.id, "name": c.name, "status": c.status, "goal_amount": float(c.goal_amount),
            "raised_amount": float(raised), "donation_count": len(counted),
            "percent_achieved": round((float(raised) / float(c.goal_amount)) * 100, 1) if c.goal_amount and c.goal_amount > 0 else None,
        })
    top_campaigns = sorted(rows, key=lambda r: r["raised_amount"], reverse=True)[:5]
    return jsonify(report={
        "total_count": len(rows),
        "by_status": _count_by(Campaign.query, Campaign.status),
        "campaigns": rows,
        "top_campaigns": top_campaigns,
    }), 200


# ---------- Expenses (Phase 6) ----------

@bp.get("/expenses")
@roles_required(*_REPORT_ROLES)
def expenses_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err

    expenses = Expense.query.filter(Expense.status.in_(EXPENSE_COUNTED_STATUSES))
    if date_from:
        expenses = expenses.filter(Expense.expense_date >= date_from)
    if date_to:
        expenses = expenses.filter(Expense.expense_date <= date_to)

    total = expenses.with_entities(db.func.coalesce(db.func.sum(Expense.amount), 0)).scalar()
    by_category_rows = expenses.with_entities(Expense.category, db.func.coalesce(db.func.sum(Expense.amount), 0)).group_by(Expense.category).all()
    by_program_rows = (
        expenses.with_entities(Expense.program_id, db.func.coalesce(db.func.sum(Expense.amount), 0))
        .group_by(Expense.program_id).all()
    )
    by_date_rows = (
        expenses.with_entities(db.func.strftime("%Y-%m", Expense.expense_date), db.func.coalesce(db.func.sum(Expense.amount), 0))
        .group_by(db.func.strftime("%Y-%m", Expense.expense_date)).order_by(db.func.strftime("%Y-%m", Expense.expense_date).asc()).all()
    )
    programs_by_id = {p.id: p.name for p in Program.query.all()}

    return jsonify(report={
        "total_count": expenses.count(),
        "total_amount": float(total),
        "by_category": [{"category": cat, "amount": float(amt)} for cat, amt in by_category_rows],
        "by_program": [{"program_id": pid or None, "program_name": programs_by_id.get(pid), "amount": float(amt)} for pid, amt in by_program_rows],
        "by_month": [{"month": m, "amount": float(amt)} for m, amt in by_date_rows],
    }), 200


@bp.get("/expenses/export.csv")
@roles_required(*_REPORT_ROLES)
def export_expenses_csv():
    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    headers = ["Date", "Category", "Amount", "Program", "Campaign", "Vendor", "Status", "Recorded By", "Description"]
    rows = [
        [
            e.expense_date.isoformat(), e.category, float(e.amount), e.program.name if e.program else "",
            e.campaign.name if e.campaign else "", e.vendor_name or "", e.status, e.recorded_by.name, e.description or "",
        ]
        for e in expenses
    ]
    return csv_response("expenses.csv", headers, rows)


# ---------- Budgets (Phase 6) ----------

@bp.get("/budgets")
@roles_required(*_REPORT_ROLES)
def budgets_report():
    budgets = Budget.query.all()
    rows = []
    for b in budgets:
        spent = budget_spent(b)
        allocated = float(b.allocated_amount)
        rows.append({
            "id": b.id, "program_id": b.program_id, "program_name": b.program.name if b.program else None,
            "allocated_amount": allocated, "spent": spent, "remaining": allocated - spent,
            "warning_level": budget_warning_level(allocated, spent),
        })
    over_budget = [r for r in rows if r["warning_level"] == "exceeded"]
    return jsonify(report={
        "total_allocated": sum(r["allocated_amount"] for r in rows),
        "total_spent": sum(r["spent"] for r in rows),
        "budgets": rows,
        "over_budget_programs": over_budget,
    }), 200


# ---------- Donors (Phase 6) ----------

@bp.get("/donors")
@roles_required(*_REPORT_ROLES)
def donors_report():
    donors = Donor.query.all()
    donations_by_donor = {}
    for d in Donation.query.filter(Donation.donor_id.isnot(None), Donation.status.in_(DONATION_COUNTED_STATUSES)).all():
        donations_by_donor.setdefault(d.donor_id, []).append(d)

    rows = []
    for donor in donors:
        donor_donations = donations_by_donor.get(donor.id, [])
        lifetime = sum((d.amount for d in donor_donations if d.amount is not None), 0)
        rows.append({"id": donor.id, "name": donor.name, "donation_count": len(donor_donations), "lifetime_amount": float(lifetime)})

    repeat_donors = sum(1 for r in rows if r["donation_count"] > 1)
    top_donors = sorted(rows, key=lambda r: r["lifetime_amount"], reverse=True)[:10]
    return jsonify(report={
        "donor_count": len(donors),
        "repeat_donors": repeat_donors,
        "top_donors": top_donors,
    }), 200


# ---------- Activities ----------

@bp.get("/activities")
@roles_required(*_REPORT_ROLES)
def activities_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    activity_type = request.args.get("activity_type")
    status = request.args.get("status")

    activities = Activity.query
    if activity_type:
        activities = activities.filter(Activity.activity_type == activity_type)
    if status:
        activities = activities.filter(Activity.status == status)
    if date_from:
        activities = activities.filter(db.func.date(Activity.scheduled_at) >= date_from.isoformat())
    if date_to:
        activities = activities.filter(db.func.date(Activity.scheduled_at) <= date_to.isoformat())

    activity_ids = [a.id for a in activities.with_entities(Activity.id).all()]
    participant_status_breakdown = (
        _count_by(ActivityParticipant.query.filter(ActivityParticipant.activity_id.in_(activity_ids)), ActivityParticipant.status)
        if activity_ids else {}
    )

    by_date_rows = (
        activities.with_entities(db.func.date(Activity.scheduled_at), db.func.count())
        .group_by(db.func.date(Activity.scheduled_at)).order_by(db.func.date(Activity.scheduled_at).asc()).all()
    )

    return jsonify(report={
        "activities_conducted": activities.count(),
        "by_type": _count_by(activities, Activity.activity_type),
        "participant_status_breakdown": participant_status_breakdown,
        "activities_by_date": [{"date": d, "count": c} for d, c in by_date_rows],
    }), 200


# ---------- Assistance requests ----------

@bp.get("/assistance")
@roles_required(*_REPORT_ROLES)
def assistance_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    request_type = request.args.get("request_type")
    assigned_to_id = request.args.get("assigned_to_id", type=int)

    requests_ = AssistanceRequest.query
    if request_type:
        requests_ = requests_.filter(AssistanceRequest.request_type == request_type)
    if assigned_to_id:
        requests_ = requests_.filter(AssistanceRequest.assigned_to_id == assigned_to_id)
    if date_from:
        requests_ = requests_.filter(db.func.date(AssistanceRequest.created_at) >= date_from.isoformat())
    if date_to:
        requests_ = requests_.filter(db.func.date(AssistanceRequest.created_at) <= date_to.isoformat())

    total = requests_.count()
    completed = requests_.filter(AssistanceRequest.status == "Completed").count()
    by_assignee_rows = (
        requests_.join(User, AssistanceRequest.assigned_to_id == User.id)
        .with_entities(User.name, db.func.count()).group_by(User.name).all()
    )

    return jsonify(report={
        "total": total,
        "by_status": _count_by(requests_, AssistanceRequest.status),
        "by_type": _count_by(requests_, AssistanceRequest.request_type),
        "by_assignee": {name: count for name, count in by_assignee_rows},
        "completion_rate": round(completed / total * 100, 1) if total else 0,
    }), 200


# ---------- Incidents ----------
# Access here is deliberately the same admin/staff ceiling as the base
# incidents module itself (see docs/api/incidents.md) — there's no
# separate "management" role in this system to grant a looser summary
# view to, so a report-level metric is exactly as restricted as the
# underlying records already are.

@bp.get("/incidents")
@roles_required(*_REPORT_ROLES)
def incidents_report():
    date_from, date_to, err = _parse_dates()
    if err:
        return err
    incident_type = request.args.get("incident_type")

    incidents = Incident.query
    if incident_type:
        incidents = incidents.filter(Incident.incident_type == incident_type)
    if date_from:
        incidents = incidents.filter(db.func.date(Incident.occurred_at) >= date_from.isoformat())
    if date_to:
        incidents = incidents.filter(db.func.date(Incident.occurred_at) <= date_to.isoformat())

    return jsonify(report={
        "total": incidents.count(),
        "by_type": _count_by(incidents, Incident.incident_type),
        "by_status": _count_by(incidents, Incident.status),
        "open": incidents.filter(Incident.status == "Open").count(),
        "follow_up_required": incidents.filter(Incident.follow_up_required.is_(True)).count(),
        "resolved": incidents.filter(Incident.status.in_(("Resolved", "Closed"))).count(),
    }), 200


@bp.get("/operational-summary")
@roles_required(*_REPORT_ROLES)
def operational_summary_report():
    """A compact, cross-module KPI snapshot — the same function the
    `generate-operational-report` CLI command uses (see cli.py), so the
    on-demand API result and a cron-generated snapshot can never
    diverge. Deliberately not a re-implementation of the other, more
    detailed per-module reports already on this blueprint."""
    return jsonify(report=reports_service.operational_summary()), 200
