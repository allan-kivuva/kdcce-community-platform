from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import ElderlyMember, HomeVisit, RecurringVisitSeries, User, VolunteerProfile
from ..notifications.service import notify
from ..utils import get_or_404, validation_error_response
from .schemas import RecurringVisitSeriesCreateSchema, RecurringVisitSeriesUpdateSchema
from .service import cancel_future_visits, generate_occurrences

bp = Blueprint("recurring_visits", __name__, url_prefix="/api/recurring-visits")

create_schema = RecurringVisitSeriesCreateSchema()
update_schema = RecurringVisitSeriesUpdateSchema()


def _member_or_400(member_id):
    if db.session.get(ElderlyMember, member_id) is None:
        return jsonify(error="Validation failed", details={"elderly_member_id": ["Elderly member not found"]}), 400
    return None


def _assignee_or_400(user_id):
    """Same rule as HomeVisit.assigned_to_id — every visit this series
    generates is a normal HomeVisit, so its assignee must already satisfy
    that model's own assignment rule (staff/admin, or a Verified
    volunteer)."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(error="Validation failed", details={"assigned_to_id": ["User not found"]}), 400
    if user.role in ("admin", "staff"):
        return None
    profile = VolunteerProfile.query.filter_by(user_id=user_id).first()
    if profile is None or profile.status != "Verified":
        return jsonify(error="Validation failed", details={"assigned_to_id": ["Can only assign staff or a verified volunteer"]}), 400
    return None


def _visit_count(series_id):
    return HomeVisit.query.filter_by(recurring_series_id=series_id).count()


@bp.post("")
@roles_required("admin", "staff")
def create_series():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    invalid = _member_or_400(data["elderly_member_id"])
    if invalid:
        return invalid
    if data.get("assigned_to_id") is not None:
        invalid = _assignee_or_400(data["assigned_to_id"])
        if invalid:
            return invalid

    data.setdefault("priority", "Medium")
    series = RecurringVisitSeries(**data, requested_by_id=int(get_jwt_identity()))
    db.session.add(series)
    db.session.flush()  # assigns series.id so generated visits can reference it

    created_visits = generate_occurrences(series, requested_by_id=int(get_jwt_identity()))
    for visit in created_visits:
        if visit.assigned_to_id:
            notify(
                visit.assigned_to_id, "Home Visit Assignment", "Home visit assigned to you",
                f"You have been assigned a home visit for {visit.elderly_member.full_name}.",
                related_resource_type="home_visit", related_resource_id=visit.id,
            )

    db.session.commit()
    return jsonify(series=series.to_dict(visit_count=len(created_visits))), 201


@bp.get("")
@roles_required("admin", "staff")
def list_series():
    query = RecurringVisitSeries.query
    elderly_member_id = request.args.get("elderly_member_id", type=int)
    if elderly_member_id:
        query = query.filter(RecurringVisitSeries.elderly_member_id == elderly_member_id)
    assigned_to_id = request.args.get("assigned_to_id", type=int)
    if assigned_to_id:
        query = query.filter(RecurringVisitSeries.assigned_to_id == assigned_to_id)
    status = request.args.get("status")
    if status:
        query = query.filter(RecurringVisitSeries.status == status)

    series_list = query.order_by(RecurringVisitSeries.created_at.desc()).all()
    return jsonify(series=[s.to_dict(visit_count=_visit_count(s.id)) for s in series_list]), 200


@bp.get("/<int:series_id>")
@roles_required("admin", "staff")
def get_series(series_id):
    series = get_or_404(RecurringVisitSeries, series_id)
    return jsonify(series=series.to_dict(visit_count=_visit_count(series.id))), 200


@bp.patch("/<int:series_id>")
@roles_required("admin", "staff")
def update_series(series_id):
    """Editing the series' own fields only — it does not retroactively
    touch already-generated HomeVisit rows (an admin/staff can still
    reassign/edit an individual generated visit via the existing
    PATCH /api/home-visits/<id>, exactly as for any other visit), except
    for one deliberate exception: transitioning to status=Cancelled also
    cancels this series' own still-open, still-future generated visits —
    otherwise a cancelled series would leave orphaned "Assigned" visits
    behind with no indication the series itself is no longer active.
    Extending end_date/occurrence_count here does not itself generate more
    occurrences — that happens on the next `generate-recurring-visits` run
    (or the next PATCH-triggered check, if this series still has room
    under the existing horizon)."""
    series = get_or_404(RecurringVisitSeries, series_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "assigned_to_id" in data and data["assigned_to_id"] is not None:
        invalid = _assignee_or_400(data["assigned_to_id"])
        if invalid:
            return invalid

    was_cancelled = series.status == "Cancelled"
    for field, value in data.items():
        setattr(series, field, value)

    cancelled_visits = []
    if series.status == "Cancelled" and not was_cancelled:
        cancelled_visits = cancel_future_visits(series)

    db.session.commit()
    return jsonify(series=series.to_dict(visit_count=_visit_count(series.id)), cancelled_visit_count=len(cancelled_visits)), 200
