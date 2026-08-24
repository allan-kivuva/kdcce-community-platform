# Feeding

`backend/app/feeding/` — meal planning and per-member meal attendance.
Depends on [elderly.md](elderly.md). Dietary requirements/restrictions are
**not** duplicated here — they already live on the elderly member record
(`allergies`, `dietary_requirements` from `GET /api/elderly/{id}`); check
that when marking attendance rather than looking for a feeding-specific
field. All endpoints require `admin` or `staff`.

Meal object:
```json
{
  "id": 1, "meal_date": "2026-08-24", "meal_type": "Lunch",
  "description": "Ugali, sukuma wiki, and beans", "planned_by": "Jane Staffer",
  "attendee_count": 12, "created_at": "...", "updated_at": "..."
}
```
`attendee_count` is only present on responses that include it (create,
list, get, update) — it's a live count, not a stored column.

Meal attendance object (append-only — no edit/delete endpoint, same as
elderly Attendance and MedicationAdministration):
```json
{ "id": 1, "meal_id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng", "elderly_member_code": "KDCCE-2026-0001", "notes": null, "recorded_by": "Jane Staffer", "created_at": "..." }
```

## POST /api/meals

- **Auth:** `admin` or `staff`.
- **Request:** `{ "meal_type": "Breakfast | Lunch | Snack | Special, required", "meal_date": "YYYY-MM-DD, optional — defaults to today", "description": "string, optional, max 2000" }`
- **Response `201`:** `{ "meal": { ... } }` (`attendee_count: 0`)
- **Errors:** `400` validation.

## GET /api/meals

- **Auth:** `admin` or `staff`.
- **Query params (optional):** `date` (`YYYY-MM-DD`), `meal_type`.
- **Response `200`:** `{ "meals": [ { ... }, ... ] }`, newest date first.
- **Errors:** `400` if `date` isn't a valid `YYYY-MM-DD` string.

## GET /api/meals/{id}
- **Auth:** `admin` or `staff`. Response `200`: `{ "meal": { ... } }`. Errors: `404`.

## PATCH /api/meals/{id}
- **Auth:** `admin` or `staff`. Partial subset of the create fields — omitted fields are left unchanged. Response `200`: `{ "meal": { ... } }`. Errors: `400`, `404`.

## DELETE /api/meals/{id}
- **Auth:** `admin` only. Response `204`. Errors: `404`; `409` if attendance has been recorded for this meal — the attendance log is permanent, so the meal it's attached to can't be deleted out from under it.

## POST /api/meals/{id}/attendance

- **Auth:** `admin` or `staff`.
- **Request:** `{ "elderly_member_id": "integer, required", "notes": "string, optional, max 1000" }`
- **Response `201`:** `{ "attendance": { ... } }`
- **Errors:** `400` unknown `elderly_member_id`; `404` unknown meal; `409` if this member is already recorded for this meal.

## GET /api/meals/{id}/attendance
- **Auth:** `admin` or `staff`. Response `200`: `{ "attendance": [ { ... }, ... ] }`, oldest first. Errors: `404`.
