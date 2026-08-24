from datetime import timedelta

from flask import Blueprint, jsonify

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import (
    Activity, ActivityParticipant, AssistanceRequest, Attendance, Donation, ElderlyMember,
    HealthRecord, HomeVisit, Incident, InventoryItem, Meal, MealAttendance,
    MedicationAdministration, StockMovement, VolunteerProfile, utcnow,
)

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

# Same reasoning as reports: every metric here is elderly-adjacent
# aggregate data volunteers have no access to at the module level. Their
# own restricted views (My Profile / My Assignments) are their dashboard.
_DASHBOARD_ROLES = ("admin", "staff")


def _daily_series(query, date_column, days):
    """One GROUP BY query per trend, not `days` separate COUNT queries.
    date_column may be a native Date column (returns a date object) or a
    db.func.date(...) expression (returns a plain string from SQLite,
    since func.date() has no declared return type) — str() normalizes
    both to 'YYYY-MM-DD' correctly (date.__str__ is also ISO format), so
    this doesn't need to know or care which kind it got."""
    start = utcnow().date() - timedelta(days=days - 1)
    rows = (
        query.filter(date_column >= start)
        .with_entities(date_column, db.func.count()).group_by(date_column).all()
    )
    counts = {str(d): c for d, c in rows}
    return [{"date": (start + timedelta(days=i)).isoformat(), "count": counts.get((start + timedelta(days=i)).isoformat(), 0)} for i in range(days)]


@bp.get("/dashboard")
@roles_required(*_DASHBOARD_ROLES)
def dashboard():
    today = utcnow().date()
    last_30 = today - timedelta(days=30)
    last_7 = today - timedelta(days=7)

    # ---------- Elderly care ----------
    total_elderly = ElderlyMember.query.count()
    new_registrations_30d = ElderlyMember.query.filter(ElderlyMember.registration_date >= last_30).count()
    today_attendance = Attendance.query.filter(Attendance.attendance_date == today).count()
    attendance_trend = _daily_series(Attendance.query, Attendance.attendance_date, 7)
    health_follow_ups = HealthRecord.query.filter(HealthRecord.follow_up_required.is_(True)).count()

    elderly_care = {
        "total_elderly_members": total_elderly,
        "new_registrations_30d": new_registrations_30d,
        "today_attendance": today_attendance,
        "attendance_trend_7d": attendance_trend,
        "follow_ups_required": health_follow_ups,
    }

    # ---------- Home & community support ----------
    home_visits = HomeVisit.query
    assistance = AssistanceRequest.query
    home_community = {
        "home_visits_pending": home_visits.filter(HomeVisit.status == "Pending").count(),
        "home_visits_active": home_visits.filter(HomeVisit.status.in_(("Assigned", "Scheduled", "In Progress"))).count(),
        "assistance_pending": assistance.filter(AssistanceRequest.status.in_(("Requested", "Matching", "Assigned", "Accepted"))).count(),
        "assistance_completed": assistance.filter(AssistanceRequest.status == "Completed").count(),
        "active_volunteers": VolunteerProfile.query.filter_by(status="Verified").count(),
    }

    # ---------- Health ----------
    health = {
        "health_checks_30d": HealthRecord.query.filter(db.func.date(HealthRecord.recorded_at) >= last_30.isoformat()).count(),
        "follow_ups_required": health_follow_ups,
        "clinic_visits": None,  # not available — module not built
        "medication_administrations_7d": MedicationAdministration.query.filter(db.func.date(MedicationAdministration.administered_at) >= last_7.isoformat()).count(),
    }

    # ---------- Feeding & resources ----------
    meals_served_7d = MealAttendance.query.join(Meal, MealAttendance.meal_id == Meal.id).filter(Meal.meal_date >= last_7).count()
    meals_trend = _daily_series(MealAttendance.query.join(Meal, MealAttendance.meal_id == Meal.id), Meal.meal_date, 7)
    # Column-vs-column comparison pushed to the database — not "load every
    # item and count in Python" (exactly what the brief warns against).
    low_stock_count = InventoryItem.query.filter(InventoryItem.current_stock <= InventoryItem.minimum_stock).count()
    donations_30d = Donation.query.filter(db.func.date(Donation.created_at) >= last_30.isoformat())
    donations_trend = _daily_series(Donation.query, db.func.date(Donation.created_at), 14)

    feeding_resources = {
        "meals_served_7d": meals_served_7d,
        "meals_trend_7d": meals_trend,
        "low_stock_items": low_stock_count,
        "inventory_movements_7d": StockMovement.query.filter(db.func.date(StockMovement.created_at) >= last_7.isoformat()).count(),
        "donations_30d": donations_30d.count(),
        "donations_trend_14d": donations_trend,
    }

    # ---------- Activities ----------
    upcoming = (
        Activity.query.filter(Activity.scheduled_at >= utcnow(), Activity.status == "Scheduled")
        .order_by(Activity.scheduled_at.asc()).limit(5).all()
    )
    attended_30d = (
        ActivityParticipant.query.join(Activity, ActivityParticipant.activity_id == Activity.id)
        .filter(ActivityParticipant.status == "Attended", db.func.date(Activity.scheduled_at) >= last_30.isoformat())
        .count()
    )
    activities = {
        "upcoming_count": Activity.query.filter(Activity.scheduled_at >= utcnow(), Activity.status == "Scheduled").count(),
        "upcoming": [{"id": a.id, "title": a.title, "activity_type": a.activity_type, "scheduled_at": a.scheduled_at.isoformat()} for a in upcoming],
        "attended_30d": attended_30d,
    }

    # ---------- Incidents ----------
    incidents_q = Incident.query
    recent_incidents = incidents_q.order_by(Incident.occurred_at.desc()).limit(5).all()
    incidents = {
        "open": incidents_q.filter(Incident.status == "Open").count(),
        "follow_up_required": incidents_q.filter(Incident.follow_up_required.is_(True)).count(),
        "recent": [
            {"id": i.id, "incident_type": i.incident_type, "status": i.status, "occurred_at": i.occurred_at.isoformat(), "elderly_member_name": i.elderly_member.full_name}
            for i in recent_incidents
        ],
    }

    return jsonify(dashboard={
        "elderly_care": elderly_care,
        "home_community": home_community,
        "health": health,
        "feeding_resources": feeding_resources,
        "activities": activities,
        "incidents": incidents,
    }), 200
