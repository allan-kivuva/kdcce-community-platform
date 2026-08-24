# Reports

`backend/app/reports/` — read-only aggregation over data every other
module already collects. No new tables — adding one here would create
exactly the "second independent calculation" the inventory module in
particular has to avoid (its `current_stock` stays sourced from
`InventoryItem`/`StockMovement` exactly as documented in
[inventory.md](inventory.md); this module never recomputes it). Every
endpoint is `admin`/`staff` only, no exceptions — each report touches
elderly-adjacent aggregate data volunteers have no access to at the module
level, and this layer must not become a backdoor around that.

Two things deliberately not reported, because the underlying data doesn't
exist: **volunteer hours** (nothing in the system records duration/time
worked — `completed_at - created_at` on a request measures workflow
latency, not hours, so it isn't presented as one) and **clinic visits**
(that module hasn't been built).

## Common query params

- `date_from`, `date_to` (`YYYY-MM-DD`) — accepted by every report except `volunteers`. Either or both may be omitted. `400` if either isn't a valid date, or if `date_to` is before `date_from`.
- Report-specific filters are listed per endpoint below — not every filter is forced onto every report (e.g. `opa_id` makes sense for attendance/health/home-visits, not for donations).

## GET /api/reports/attendance

- **Filters:** `date_from`, `date_to`, `opa_id`.
- **Response `200`:**
  ```json
  {
    "report": {
      "registered_count": 126, "total_records": 1824, "checked_out": 1780,
      "still_checked_in": 44, "by_day": [{ "date": "2026-08-01", "count": 73 }],
      "average_daily": 73.0, "highest_day": 92, "lowest_day": 51,
      "attendance_percentage": 58.0
    }
  }
  ```
  `average_daily`/`attendance_percentage` are computed against days that actually had attendance records, not raw calendar days, so a centre closed on Sundays isn't penalized. `attendance_percentage` uses distinct (member, day) pairs against the registered roster.

### GET /api/reports/attendance/export.csv
Same filters. Columns: Date, Attendance Count.

## GET /api/reports/health

- **Filters:** `date_from`, `date_to`, `opa_id`.
- **Response `200`:** `health_checks_completed`, `follow_ups_required`, `wellness_trend` (count per recorded `wellbeing` value — a tally, not a diagnosis), `medications_started`, `medication_administration` (count per `Given`/`Missed`/`Refused`), `clinic_visits: null` (not available).

## GET /api/reports/home-visits

- **Filters:** `date_from`, `date_to`, `opa_id`, `volunteer_id` (matches `assigned_to_id`).
- **Response `200`:** `total`, `by_status`, `follow_up_required`, `by_volunteer` (name → count, assigned visits only).

### GET /api/reports/home-visits/export.csv
Same filters (`date_from`/`date_to`/`opa_id`). Columns: Elderly Member, Status, Priority, Assigned To, Created.

## GET /api/reports/volunteers — Volunteer Performance

- **Filters:** none.
- **Response `200`:** `by_status` (Pending/Verified/Rejected counts), `active_volunteers` (Verified count), `workload`: one entry per Verified volunteer with:
  - `home_visits_total`/`home_visits_completed`, `assistance_requests_total`/`assistance_requests_completed`
  - `active_assignments` (currently open across both), `pending_assignments` (`total - completed - cancelled`), `cancelled_assignments`
  - `completion_rate` (percentage, `0.0` if the volunteer has zero assignments — never a division error)
  - `assigned_elderly_count` — distinct elderly members across this volunteer's currently-active (not completed/cancelled) home visits
  - `follow_ups_completed` — this volunteer's completed [follow-ups](followups.md)

  Still one small query loop per volunteer (not a single mega-query) — same as before this was extended, bounded by how many volunteers exist, not by their history size. No "volunteer hours": nothing in this system records duration/time-on-task, so that number would be fabricated, not measured.

## GET /api/reports/feeding

- **Filters:** `date_from`, `date_to`.
- **Response `200`:** `meals_planned`, `meals_served` (attendance rows — existence of a `MealAttendance` row means served, per [feeding.md](feeding.md)), `meals_by_date`, `dietary_flagged_attendees` (distinct members served in range who have `allergies`/`dietary_requirements` set — a count, not a list of who).

## GET /api/reports/inventory

- **Filters:** `date_from`, `date_to` (apply to movements only, not the current item list), `category`.
- **Response `200`:** `items` (full `InventoryItem.to_dict()` list — the same `current_stock`/`low_stock` the inventory module itself reports), `low_stock_items`, `stock_in_total`/`stock_out_total` (summed quantity in range), `movements_by_date`, `donation_linked_movements` (count of in-range movements with a `donation_id`).

### GET /api/reports/inventory/export.csv
Filters: `date_from`, `date_to`, `category`. Columns: Item, Type, Quantity, Reason, Recorded By, Date — movements, not the item list.

## GET /api/reports/donations

- **Filters:** `date_from`, `date_to`, `donation_type`.
- **Response `200`:** `total_count`, `by_type`, `cash_total` (sum of `amount` for Cash donations only), `by_date`.

## GET /api/reports/donations/history

Paginated, filtered donation rows — complements the existing unfiltered
`GET /api/donations` (used by the admin donations manager UI) for when a
report needs a specific date range or type over what could be a large
history.

- **Filters:** `date_from`, `date_to`, `donation_type`, `page` (default 1), `per_page` (default 25, max 100).
- **Response `200`:** `{ "donations": [...], "pagination": { "page", "per_page", "total", "pages" } }`.

## GET /api/reports/activities

- **Filters:** `date_from`, `date_to`, `activity_type`, `status`.
- **Response `200`:** `activities_conducted`, `by_type`, `participant_status_breakdown` (Registered/Attended/No-show/Cancelled across matching activities), `activities_by_date`.

## GET /api/reports/assistance

- **Filters:** `date_from`, `date_to`, `request_type`, `assigned_to_id`.
- **Response `200`:** `total`, `by_status`, `by_type`, `by_assignee`, `completion_rate` (% with `status: "Completed"`).

## GET /api/reports/incidents

Access here is the same admin/staff ceiling as the base
[incidents](incidents.md) module — there's no separate "management" role
in this system to grant a looser summary view to, so the report is exactly
as restricted as the underlying records already are.

- **Filters:** `date_from`, `date_to`, `incident_type`.
- **Response `200`:** `total`, `by_type`, `by_status`, `open`, `follow_up_required`, `resolved` (Resolved + Closed).
