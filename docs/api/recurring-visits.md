# Recurring home visits

`backend/app/recurring_visits/` — a recurring schedule that materializes
real [`HomeVisit`](home-visits.md) rows, rather than a new kind of
visit. Depends on [elderly.md](elderly.md) and
[volunteers.md](volunteers.md) (`assigned_to_id` follows the exact same
rule as `HomeVisit.assigned_to_id`). Every visit a series generates is a
completely ordinary `HomeVisit` — assignable, acceptable, completable,
reviewable, through the exact same endpoints as a one-off visit — just
linked back to its series via `HomeVisit.recurring_series_id` for
traceability (same optional-link pattern as
`AssistanceRequest.home_visit_id`).

**No background scheduler or job queue.** Occurrences are generated (a)
up front, through a fixed 60-day horizon, the moment a series is created,
and (b) topped up later by the `flask generate-recurring-visits` CLI
command — meant to be run on a plain OS cron (daily, say), the same way
this app already expects `seed-admin`/`seed-demo` to be run manually, not
a new kind of infrastructure. Never running the CLI command is safe (the
series simply never generates further than its initial batch); running it
repeatedly is also safe — see idempotency below.

**Idempotent, gap-free generation.** Occurrence `N`'s calendar date is
always computed directly from `(start_date, frequency, N)` — weekly/
biweekly by simple day-count, monthly via calendar-month arithmetic
clamped to the target month's actual length (so e.g. a series anchored on
the 31st correctly lands on Feb 28/29, then back to the 31st in a
31-day month — never drifting to the 28th permanently). `occurrences_generated`
is the only bookkeeping needed to resume: generation always starts at
`N = occurrences_generated` and never revisits an earlier `N`, so a second
generation call with the same (or an earlier) horizon creates nothing new.

Series object:
```json
{
  "id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng",
  "elderly_member_code": "KDCCE-2026-0001",
  "assigned_to_id": 4, "assigned_to": "Grace Mwangi", "requested_by": "Jane Staffer",
  "reason": "Weekly wellbeing check", "priority": "Medium",
  "frequency": "weekly", "start_date": "2026-03-02", "scheduled_time": "09:00",
  "end_date": null, "occurrence_count": null, "occurrences_generated": 9,
  "status": "Active", "created_at": "...", "updated_at": "...",
  "visit_count": 9
}
```
`frequency`: `weekly | biweekly | monthly`. `status`: `Active | Paused |
Cancelled` — only `Active` series generate further occurrences.
`visit_count` (present on `GET`/`POST` responses, not stored) is the
number of `HomeVisit` rows this series has actually generated so far —
normally equal to `occurrences_generated`, included for convenience so a
caller doesn't need a second request to know how many visits exist.

## POST /api/recurring-visits

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "elderly_member_id": "integer, required",
    "assigned_to_id": "integer, optional — must be staff/admin or a Verified volunteer",
    "reason": "string, required, max 2000",
    "priority": "Low | Medium | High | Urgent, optional, default Medium",
    "frequency": "weekly | biweekly | monthly, required",
    "start_date": "YYYY-MM-DD, required — also the recurrence anchor day",
    "scheduled_time": "HH:MM, optional, default 09:00",
    "end_date": "YYYY-MM-DD, optional",
    "occurrence_count": "integer >= 1, optional"
  }
  ```
  Immediately generates every occurrence due within the next 60 days (or
  fewer, if `end_date`/`occurrence_count` is reached first) — each one a
  real `HomeVisit`, `Assigned` if `assigned_to_id` was given (and
  notifying that assignee, same as a normal home visit) or `Pending`
  otherwise.
- **Response `201`:** `{ "series": { ... } }`
- **Errors:** `400` (unknown `elderly_member_id`, or `assigned_to_id` that isn't staff/admin/verified-volunteer, or `end_date` before `start_date`), `403` (not admin/staff).

## GET /api/recurring-visits

- **Auth:** `admin` or `staff`.
- **Query params (optional):** `elderly_member_id`, `assigned_to_id`, `status`.
- **Response `200`:** `{ "series": [ { ... }, ... ] }`, newest first.

## GET /api/recurring-visits/{id}
- **Auth:** `admin` or `staff`. Response `200`: `{ "series": { ... } }`. Errors: `404`.

## PATCH /api/recurring-visits/{id}

- **Auth:** `admin` or `staff`.
- **Request:** any subset of `assigned_to_id`, `reason`, `priority`, `end_date`, `occurrence_count`, `status`. **`frequency` and `start_date` are not editable** — changing the recurrence pattern after occurrences already exist would desync already-generated dates from the new pattern; cancel this series and create a new one instead. Sending either is rejected as an unknown field (`400`).
- Does **not** itself generate more occurrences (extending `end_date`/`occurrence_count` takes effect on the next CLI top-up), and does **not** retroactively touch already-generated `HomeVisit` rows — reassign/edit an individual one via the existing `PATCH /api/home-visits/{id}`, exactly as for any other visit.
- **Exception:** transitioning `status` to `Cancelled` also cancels this series' own still-open (`status` not `Completed`/`Cancelled`), still-future (`scheduled_at` in the future) generated visits — otherwise a cancelled series would leave orphaned `Assigned` visits behind. Already-`Completed` visits are historical record and are left untouched.
- **Response `200`:** `{ "series": { ... }, "cancelled_visit_count": 0 }` — the count is always present, `0` unless this PATCH just cancelled the series.
- **Errors:** `400`, `403`, `404`.

No `DELETE` endpoint — a series that generated real visit history is
corrected via `status: "Cancelled"`, never removed, same reasoning as
[Incidents](incidents.md).
