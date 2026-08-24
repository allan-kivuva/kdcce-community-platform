# Analytics

`backend/app/analytics/` — the at-a-glance management dashboard. This is
a different question from [reports](reports.md): reports answer "give me
the detailed, filterable breakdown"; this answers "what does today look
like." One endpoint, cheap `COUNT`-only aggregates plus three short trend
series — not a rehash of every report as a chart. `admin`/`staff` only,
same reasoning as reports: every metric is elderly-adjacent aggregate data
volunteers have no module-level access to; their own restricted views (My
Profile, My Assignments, My Assistance Requests) are their dashboard.

The existing `Overview` page at `/admin` (donation/blog/craft stats, left
over from the original public-site admin panel) is untouched — this is
new, separate functionality, not a rewrite of it.

## GET /api/analytics/dashboard

- **Auth:** `admin` or `staff`.
- **Response `200`:**
  ```json
  {
    "dashboard": {
      "elderly_care": {
        "total_elderly_members": 126, "new_registrations_30d": 4,
        "today_attendance": 73, "attendance_trend_7d": [{ "date": "2026-08-18", "count": 68 }, "... 7 entries, oldest to newest"],
        "follow_ups_required": 5
      },
      "home_community": {
        "home_visits_pending": 3, "home_visits_active": 7,
        "assistance_pending": 2, "assistance_completed": 41,
        "active_volunteers": 12
      },
      "health": {
        "health_checks_30d": 58, "follow_ups_required": 5,
        "clinic_visits": null, "medication_administrations_7d": 34
      },
      "feeding_resources": {
        "meals_served_7d": 210, "meals_trend_7d": ["... 7 entries"],
        "low_stock_items": 2, "inventory_movements_7d": 9,
        "donations_30d": 14, "donations_trend_14d": ["... 14 entries"]
      },
      "activities": {
        "upcoming_count": 3,
        "upcoming": [{ "id": 1, "title": "Morning Walk", "activity_type": "Walking", "scheduled_at": "..." }],
        "attended_30d": 47
      },
      "incidents": {
        "open": 1, "critical_open": 0, "follow_up_required": 1,
        "recent": [{ "id": 1, "incident_type": "Fall", "severity": "Medium", "status": "Open", "occurred_at": "...", "elderly_member_name": "Mary Achieng" }]
      },
      "follow_ups": { "pending": 4, "overdue": 1 },
      "upcoming_visits": {
        "count": 3,
        "upcoming": [{ "id": 1, "elderly_member_name": "Mary Achieng", "assigned_to": "Grace Mwangi", "scheduled_at": "..." }]
      },
      "volunteer_performance": {
        "active_volunteers": 5, "total_assignments": 23, "completed_assignments": 3, "completion_rate": 13.0
      },
      "today_activity": {
        "attendance": [{ "id": 1, "elderly_member_name": "Mary Achieng", "check_in_at": "..." }],
        "home_visits": [{ "id": 1, "elderly_member_name": "Mary Achieng", "status": "Completed" }],
        "assistance_requests": [{ "id": 1, "elderly_member_name": "Mary Achieng", "status": "Requested" }],
        "health_observations": [{ "id": 1, "elderly_member_name": "Mary Achieng", "wellbeing": "Good" }]
      }
    }
  }
  ```

Notes:
- `follow_ups`/`upcoming_visits`/`volunteer_performance`/`today_activity`
  are additive — this is still the one existing dashboard endpoint,
  extended, not a second one. `volunteer_performance` here is a
  lightweight aggregate (a handful of bounded `COUNT` queries, no loop
  over volunteers) — for the full per-volunteer breakdown, see
  [reports.md](reports.md#get-apireportsvolunteers--volunteer-performance),
  which this deliberately doesn't duplicate.
- `upcoming_visits` includes any not-yet-happened visit that isn't
  `Completed`/`Cancelled` — including a still-`Pending` (unassigned)
  scheduled visit, since that's the one that most needs attention, not
  just `Assigned`/`Scheduled` ones.
- `today_activity` lists (not just counts) — each capped at 5, matching
  the existing `recent`/`upcoming` list precedent already used elsewhere
  in this endpoint.
- `clinic_visits: null` — that module doesn't exist yet, not fabricated.
- No "volunteer hours" anywhere — same reasoning as [reports.md](reports.md): nothing records duration/time-on-task.
- Trend arrays are always zero-filled and exactly `7`/`14` entries long, oldest to newest, anchored on today regardless of whether any data exists for a given day — a quiet week doesn't produce a shorter array.
- `incidents.recent` deliberately omits `description`/`immediate_action_taken`/`resolution_notes` — a dashboard tile shows what happened in outline (type, status, date, who), not the sensitive narrative.
- `low_stock_items` is a single column-vs-column database comparison (`current_stock <= minimum_stock`), not a full item-list fetch counted in Python.
