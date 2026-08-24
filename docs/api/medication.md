# Medication

`backend/app/medication/` — prescribed medications and a per-dose
administration log. There is no automated push-reminder system yet
(that's Phase 7/notifications) — "reminders" today means the Active
medications list itself. All endpoints require `admin` or `staff`.
Depends on [elderly.md](elderly.md).

Medication object:
```json
{
  "id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng",
  "elderly_member_code": "KDCCE-2026-0001", "name": "Amlodipine",
  "dosage": "5mg", "instructions": "Take with food", "schedule": "Once daily",
  "start_date": "2026-08-24", "end_date": null, "status": "Active",
  "notes": null, "created_by": "Jane Staffer", "created_at": "...", "updated_at": "..."
}
```

Administration (dose log) object:
```json
{ "id": 1, "medication_id": 1, "administered_at": "...", "status": "Given", "notes": null, "administered_by": "Jane Staffer", "created_at": "..." }
```

## POST /api/medications

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "elderly_member_id": "integer, required",
    "name": "string, required, max 150",
    "dosage": "string, optional, max 100",
    "instructions": "string, optional, max 2000",
    "schedule": "string, optional, max 100 (free text, e.g. \"Twice daily\")",
    "start_date": "YYYY-MM-DD, optional — defaults to today",
    "end_date": "YYYY-MM-DD, optional",
    "status": "Active | Completed | Discontinued, optional, default Active",
    "notes": "string, optional, max 2000"
  }
  ```
- **Response `201`:** `{ "medication": { ... } }`
- **Errors:** `400` validation (includes an unknown `elderly_member_id`).

## GET /api/medications

- **Auth:** `admin` or `staff`.
- **Query params (all optional):** `elderly_member_id`, `status`.
- **Response `200`:** `{ "medications": [ { ... }, ... ] }`, newest first.

## GET /api/medications/{id}
- **Auth:** `admin` or `staff`. Response `200`: `{ "medication": { ... } }`. Errors: `404`.

## PATCH /api/medications/{id}

- **Auth:** `admin` or `staff`. Partial subset of the create fields — **omitted fields are left unchanged** (in particular, omitting `status` does not reset it back to `Active`). This is the endpoint for changing status, e.g. `{ "status": "Discontinued" }`.
- **Response `200`:** `{ "medication": { ... } }`. Errors: `400`, `404`.

## DELETE /api/medications/{id}

- **Auth:** `admin` only.
- **Response `204`.**
- **Errors:** `404`; `409` if this medication has administration log entries — delete only applies to a mistaken entry with no history. Set `status` to `Discontinued` instead of deleting a medication that was actually given.

## POST /api/medications/{id}/administrations

Log one dose event. There is no edit/delete on these — it's an append-only log.

- **Auth:** `admin` or `staff`.
- **Request:** `{ "status": "Given | Missed | Refused, optional, default Given", "notes": "string, optional, max 2000" }`
- **Response `201`:** `{ "administration": { ... } }`
- **Errors:** `400` invalid status; `404` unknown medication.

## GET /api/medications/{id}/administrations
- **Auth:** `admin` or `staff`. Response `200`: `{ "administrations": [ { ... }, ... ] }`, newest first. Errors: `404`.
