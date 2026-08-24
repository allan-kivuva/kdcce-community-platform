# Assignment calendar

`backend/app/calendar/` — a read-only aggregation over the two existing
scheduling fields (`HomeVisit.scheduled_at`, `AssistanceRequest.scheduled_at`).
No new model — the calendar is a view over data that already exists.

## GET /api/calendar
- **Auth:** any valid token.
  - `admin`/`staff`: every scheduled home visit and assistance request.
  - `volunteer`: only their own (`assigned_to_id == you`) — exactly the
    same scoping rule already used for `/api/home-visits` and
    `/api/assistance-requests`, not a new authorization concept.
- **Query params (optional):** `start`, `end` (`YYYY-MM-DD`) — filters on `scheduled_at`.
- **Response `200`:**
  ```json
  { "events": [
    { "id": 4, "type": "home_visit", "elderly_member_id": 3, "elderly_member_name": "Alice Wambui",
      "assigned_to_id": 5, "assigned_to": "Grace Mwangi", "scheduled_at": "2026-08-25T10:00:00+00:00", "status": "Assigned" }
  ] }
  ```
  `type` is `home_visit` or `assistance_request`. Sorted by `scheduled_at`
  ascending. A visit/request with no `scheduled_at` set never appears here
  (it has nothing to put on a calendar) — it's still fully visible via its
  own module's endpoints.
- **Errors:** `401`, `403` (a role that's neither `volunteer` nor `admin`/`staff` — not reachable in practice today, since every account has one of those roles).
