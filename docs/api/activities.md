# Activities

`backend/app/activities/` — events/classes (exercise, games, social,
educational, etc.) with participant registration and attendance. Depends
on [elderly.md](elderly.md) and [volunteers.md](volunteers.md)
(`facilitator_id` follows the same rule as `HomeVisit.assigned_to_id` —
see [home-visits.md](home-visits.md) — staff/admin or a `Verified`
volunteer only). All endpoints require `admin` or `staff`.

Activity object:
```json
{
  "id": 1, "title": "Morning Walk", "activity_type": "Walking",
  "description": null, "location": "Community garden",
  "scheduled_at": "2026-08-24T09:00:00+00:00",
  "facilitator_id": 4, "facilitator": "Grace Mwangi",
  "status": "Scheduled", "participant_count": 3,
  "created_by": "Jane Staffer", "created_at": "...", "updated_at": "..."
}
```
`activity_type` is one of `Exercise | Walking | Games | Social |
Intergenerational | Skills Training | Educational | Community Event |
Other`. `status` is `Scheduled | In Progress | Completed | Cancelled` — no
enforced state machine, same as every other module here. `participant_count`
is a live query, not a stored column.

Participant object — **registration and attendance are the same row**,
not two separate records: registering ahead of time and marking who
showed up are the same relationship at different points in its lifecycle
(`status`: `Registered | Attended | No-show | Cancelled`):
```json
{ "id": 1, "activity_id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng", "elderly_member_code": "KDCCE-2026-0001", "status": "Registered", "notes": null, "recorded_by": "Jane Staffer", "created_at": "...", "updated_at": "..." }
```

## POST /api/activities

- **Request:** `{ "title": "string, required, max 150", "activity_type": "required, see above", "description": "optional, max 2000", "location": "optional, max 150", "scheduled_at": "ISO datetime, required", "facilitator_id": "integer, optional — staff/admin or a Verified volunteer" }`
- **Response `201`:** `{ "activity": { ... } }` (`status` always starts `Scheduled`, `participant_count: 0`)
- **Errors:** `400` validation, including a `facilitator_id` that isn't staff/admin/verified-volunteer.

## GET /api/activities
- **Query params (optional):** `date` (`YYYY-MM-DD`, matches the date part of `scheduled_at`), `activity_type`, `status`.
- **Response `200`:** `{ "activities": [ { ... }, ... ] }`, newest scheduled first.
- **Errors:** `400` bad `date` format.

## GET /api/activities/{id}
- Response `200`: `{ "activity": { ... } }`. Errors: `404`.

## PATCH /api/activities/{id}
- Partial subset of the create fields plus `status`. Omitted fields are left unchanged, never reset. Errors: `400`, `404`.

## DELETE /api/activities/{id}
- **Auth:** `admin` only. Errors: `404`; `409` if the activity has registered participants.

## POST /api/activities/{id}/participants
- **Request:** `{ "elderly_member_id": "integer, required", "notes": "optional, max 1000" }` — starts at `status: "Registered"`.
- **Errors:** `400` unknown member; `404` unknown activity; `409` already registered.

## GET /api/activities/{id}/participants
- Response `200`: `{ "participants": [ { ... }, ... ] }`, registration order.

## PATCH /api/activities/{id}/participants/{participant_id}
- **Request:** `{ "status": "Registered | Attended | No-show | Cancelled", "notes": "optional" }` — this is how attendance gets marked (`status: "Attended"`). Errors: `400`, `404`.
