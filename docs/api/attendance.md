# Attendance

`backend/app/attendance/` — daily check-in/check-out for elderly members.
Depends on [elderly.md](elderly.md) (an attendance record always points at
an existing elderly member). All endpoints require `admin` or `staff`.

Attendance record object:
```json
{
  "id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng",
  "elderly_member_code": "KDCCE-2026-0001", "attendance_date": "2026-08-24",
  "check_in_at": "2026-08-24T08:15:00+00:00", "check_out_at": null,
  "recorded_by": "Jane Staffer", "notes": null, "created_at": "..."
}
```

## POST /api/attendance/check-in

- **Auth:** `admin` or `staff`.
- **Request:** `{ "elderly_member_id": "integer, required", "notes": "string, optional, max 2000" }`
- **Response `201`:** `{ "attendance": { ... } }`
- **Errors:** `400` if `elderly_member_id` doesn't exist; `409` if that member already has an open (not checked-out) record for today — check them out first, or use the existing record.

## PATCH /api/attendance/{id}/check-out

- **Auth:** `admin` or `staff`.
- **Request:** `{ "notes": "string, optional, max 2000" }` — replaces the record's notes if given, otherwise leaves them as set at check-in.
- **Response `200`:** `{ "attendance": { ... } }`, `check_out_at` now set.
- **Errors:** `404`; `409` if already checked out.

## GET /api/attendance

- **Auth:** `admin` or `staff`.
- **Query params (all optional):** `date` (`YYYY-MM-DD`, defaults to returning all dates if omitted — the frontend's "Today" view always passes today's date explicitly), `elderly_member_id`, `opa_id` (via the member's OPA).
- **Response `200`:** `{ "attendance": [ { ... }, ... ] }`, newest check-in first.
- **Errors:** `400` if `date` isn't a valid `YYYY-MM-DD` string.
