import calendar
from datetime import date, datetime, timedelta, timezone

from ..extensions import db
from ..models import HomeVisit, utcnow

# How far ahead a series gets materialized, both at creation and by the
# `generate-recurring-visits` CLI top-up — a fixed horizon rather than
# "everything up to end_date/occurrence_count", so an open-ended series
# (no end_date, no occurrence_count) doesn't try to insert years of rows
# in one call. Re-running generation later naturally extends the horizon
# further, via occurrences_generated (see RecurringVisitSeries's docstring).
GENERATION_HORIZON_DAYS = 60


def add_months(d, n):
    """`d` shifted forward by `n` calendar months, with the day clamped to
    the target month's actual length (e.g. Jan 31 + 1 month -> Feb 28/29,
    never Mar 3). Used only for monthly recurrence — this clamping, plus
    always computing from the fixed anchor date rather than stepping off
    the previous (possibly-already-clamped) occurrence, is what keeps a
    monthly series anchored to its original day-of-month instead of
    drifting shorter every time it crosses a short month."""
    total_month_index = d.month - 1 + n
    year = d.year + total_month_index // 12
    month = total_month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


def occurrence_date(start_date, frequency, n):
    """The calendar date of occurrence index `n` (0-based, n=0 is
    start_date itself). Deterministic and independent of any other
    occurrence — never derived by stepping off occurrence n-1 — so
    resuming generation at any n, in any order, always produces the same
    date every time (no drift, no dependency on what's already been
    generated)."""
    if frequency == "weekly":
        return start_date + timedelta(weeks=n)
    if frequency == "biweekly":
        return start_date + timedelta(weeks=2 * n)
    if frequency == "monthly":
        return add_months(start_date, n)
    raise ValueError(f"Unknown frequency: {frequency}")


def generate_occurrences(series, through_date=None, requested_by_id=None):
    """Materializes HomeVisit rows for `series` from its current
    occurrences_generated up through `through_date` (default: today +
    GENERATION_HORIZON_DAYS), stopping early at occurrence_count or
    end_date, whichever applies. Idempotent and gap-free by construction:
    it only ever appends starting at n = series.occurrences_generated and
    advances that counter by exactly the number of rows it creates — a
    second call with the same or an earlier through_date creates nothing
    new. Does not commit; caller commits as part of its own transaction
    (same convention as notify()).

    Returns the list of newly-created HomeVisit rows (possibly empty).
    """
    if series.status != "Active":
        return []

    if through_date is None:
        through_date = utcnow().date() + timedelta(days=GENERATION_HORIZON_DAYS)

    created = []
    n = series.occurrences_generated
    while True:
        if series.occurrence_count is not None and n >= series.occurrence_count:
            break
        occ_date = occurrence_date(series.start_date, series.frequency, n)
        if series.end_date is not None and occ_date > series.end_date:
            break
        if occ_date > through_date:
            break

        # scheduled_time is a plain (no-tzinfo) Time column — combined here
        # as UTC, matching utcnow()'s convention for every other server-set
        # timestamp in this app.
        scheduled_at = datetime.combine(occ_date, series.scheduled_time, tzinfo=timezone.utc)
        visit = HomeVisit(
            elderly_member_id=series.elderly_member_id,
            requested_by_id=requested_by_id or series.requested_by_id,
            assigned_to_id=series.assigned_to_id,
            recurring_series_id=series.id,
            priority=series.priority,
            status="Assigned" if series.assigned_to_id else "Pending",
            reason=series.reason,
            scheduled_at=scheduled_at,
        )
        db.session.add(visit)
        created.append(visit)
        n += 1

    series.occurrences_generated = n
    if created:
        db.session.flush()  # assigns ids on the new visits for the caller/response
    return created


def cancel_future_visits(series):
    """Called when a series is cancelled: stops any of its already-
    generated visits that are still in a non-terminal state and still in
    the future from continuing to sit on someone's calendar/assignment
    list as if the series were still active. Completed visits (real,
    already-performed work) and visits already Cancelled individually are
    left untouched — this only reaches forward, never rewrites history."""
    now = utcnow()
    future_open_visits = HomeVisit.query.filter(
        HomeVisit.recurring_series_id == series.id,
        HomeVisit.status.notin_(("Completed", "Cancelled")),
        HomeVisit.scheduled_at.isnot(None),
        HomeVisit.scheduled_at >= now,
    ).all()
    for visit in future_open_visits:
        visit.status = "Cancelled"
    return future_open_visits
