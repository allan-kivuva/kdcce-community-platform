# Health & wellness

`backend/app/health/` — point-in-time wellness observations for an elderly
member. This is purely a record of what staff observed, never an automated
interpretation or diagnosis. All endpoints require `admin` or `staff`.
Depends on [elderly.md](elderly.md).

Health record object:
```json
{
  "id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng",
  "elderly_member_code": "KDCCE-2026-0001", "recorded_at": "2026-08-24T09:00:00+00:00",
  "blood_pressure_systolic": 130, "blood_pressure_diastolic": 85,
  "temperature_celsius": 36.8, "pulse_bpm": 72, "weight_kg": 61.5,
  "wellbeing": "Good", "mood": "Cheerful", "physical_activity": "Walked 20 minutes",
  "observations": null, "follow_up_required": false, "follow_up_notes": null,
  "recorded_by": "Jane Staffer", "created_at": "..."
}
```

**`follow_up_required: true` auto-creates a [FollowUp](followups.md)** —
on creation, or on a `PATCH` that transitions it `False → True`. Re-saving
an already-`true` flag does not create a second one.

## POST /api/health-records

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "elderly_member_id": "integer, required",
    "recorded_at": "ISO datetime, optional — defaults to now",
    "blood_pressure_systolic": "integer 1-400, optional",
    "blood_pressure_diastolic": "integer 1-300, optional",
    "temperature_celsius": "number 20-45, optional",
    "pulse_bpm": "integer 1-300, optional",
    "weight_kg": "number 1-400, optional",
    "wellbeing": "Good | Fair | Poor, optional",
    "mood": "string, optional, max 60",
    "physical_activity": "string, optional, max 1000",
    "observations": "string, optional, max 4000",
    "follow_up_required": "boolean, optional, default false",
    "follow_up_notes": "string, optional, max 2000"
  }
  ```
- **Response `201`:** `{ "record": { ... } }`
- **Errors:** `400` validation (includes an unknown `elderly_member_id` or an out-of-range vital).

## GET /api/health-records

- **Auth:** `admin` or `staff`.
- **Query params (all optional):** `elderly_member_id`, `follow_up_required` (`true`/`false`).
- **Response `200`:** `{ "records": [ { ... }, ... ] }`, newest first.

## GET /api/health-records/{id}
- **Auth:** `admin` or `staff`. Response `200`: `{ "record": { ... } }`. Errors: `404`.

## PATCH /api/health-records/{id}

- **Auth:** `admin` or `staff`. Partial subset of the create fields — **omitted fields are left unchanged**, they are never reset to a default (in particular, omitting `follow_up_required` or `recorded_at` does not clear/reset them).
- **Response `200`:** `{ "record": { ... } }`. Errors: `400`, `404`.

## DELETE /api/health-records/{id}
- **Auth:** `admin` only. Response `204`. Errors: `404`.
