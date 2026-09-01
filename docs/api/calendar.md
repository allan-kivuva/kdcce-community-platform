# Assignment calendar

`backend/app/calendar/` — a read-only aggregation over three existing
scheduling fields (`HomeVisit.scheduled_at`, `AssistanceRequest.scheduled_at`,
`Activity.scheduled_at`). No new model — the calendar is a view over data
that already exists.

## GET /api/calendar
- **Auth:** any valid token.
  - `admin`/`staff`: every scheduled home visit, assistance request, and activity.
  - `volunteer`: only their own — home visits/requests via `assigned_to_id == you`,
    activities via `facilitator_id == you` — exactly the same scoping rule
    already used for `/api/home-visits`, `/api/assistance-requests`, and
    (implicitly) activity facilitation, not a new authorization concept.
- **Query params (optional):** `start`, `end` (`YYYY-MM-DD`) — filters on `scheduled_at`.
- **Response `200`:**
  ```json
  { "events": [
    { "id": 4, "type": "home_visit", "elderly_member_id": 3, "elderly_member_name": "Alice Wambui",
      "assigned_to_id": 5, "assigned_to": "Grace Mwangi", "scheduled_at": "2026-08-25T10:00:00+00:00", "status": "Assigned" },
    { "id": 2, "type": "activity", "elderly_member_id": null, "elderly_member_name": null, "title": "Morning Walk",
      "assigned_to_id": 5, "assigned_to": "Grace Mwangi", "scheduled_at": "2026-08-25T09:00:00+00:00",
      "status": "Scheduled", "activity_type": "Walking" }
  ] }
  ```
  `type` is `home_visit`, `assistance_request`, or `activity`. Sorted by
  `scheduled_at` ascending. A visit/request with no `scheduled_at` set never
  appears here (it has nothing to put on a calendar) — it's still fully
  visible via its own module's endpoints; `Activity.scheduled_at` is always
  set, so every activity appears. `title`/`activity_type` are only present
  on `activity` events — new, additive fields; existing consumers reading
  only `home_visit`/`assistance_request` events are unaffected.
  `assigned_to_id`/`assigned_to` on an `activity` event point at its
  facilitator, reusing the same key names as the other two types for a
  uniform shape.
- **Errors:** `401`, `403` (a role that's neither `volunteer` nor `admin`/`staff` — not reachable in practice today, since every account has one of those roles).
