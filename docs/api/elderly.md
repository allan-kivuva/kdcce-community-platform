# Elderly members & OPAs

`backend/app/elderly/` — elderly member records and the OPA (Older Persons
Association / community group) they optionally belong to. Every endpoint
here requires `admin` or `staff` — volunteers have no access to elderly
records at all; there is no public route.

OPA object:
```json
{ "id": 1, "name": "Kibera OPA", "location": "Kibera", "description": null, "created_at": "...", "updated_at": "..." }
```

Elderly member object:
```json
{
  "id": 1, "member_id": "KDCCE-2026-0001", "full_name": "Mary Achieng",
  "date_of_birth": "1948-03-12", "gender": "Female", "location": "Kibera",
  "opa_id": 1, "opa_name": "Kibera OPA",
  "emergency_contact_name": "James Achieng", "emergency_contact_phone": "0712345678",
  "emergency_contact_relationship": "Son",
  "vulnerability_notes": null, "health_notes": "Uses a walking stick",
  "allergies": "Penicillin", "dietary_requirements": "Low salt",
  "registration_date": "2026-08-24", "status": "Active",
  "created_at": "...", "updated_at": "..."
}
```

`member_id` is always server-generated (`KDCCE-<year>-<zero-padded id>`),
never client-supplied.

## OPAs

### GET /api/opas
- **Auth:** `admin` or `staff`. Response `200`: `{ "opas": [ { ... }, ... ] }`, alphabetical.

### POST /api/opas
- **Auth:** `admin` or `staff`.
- **Request:** `{ "name": "string, required, max 150", "location": "string, optional, max 150", "description": "string, optional, max 2000" }`
- **Response `201`:** `{ "opa": { ... } }`
- **Errors:** `400` validation; `409` if the name already exists.

### PATCH /api/opas/{id}
- **Auth:** `admin` or `staff`. Partial subset of the create fields. Response `200`: `{ "opa": { ... } }`. Errors: `400`, `404`.

### DELETE /api/opas/{id}
- **Auth:** `admin` or `staff`. Response `204`. Any elderly member pointing at this OPA has `opa_id` set to `null`, not deleted. Errors: `404`.

## Elderly members

### GET /api/elderly
- **Auth:** `admin` or `staff`.
- **Query params (all optional):** `q` (matches `full_name` or `member_id`, case-insensitive substring), `status` (one of the statuses below), `opa_id` (integer).
- **Response `200`:** `{ "members": [ { ... }, ... ] }`, alphabetical by name.

### GET /api/elderly/{id}
- **Auth:** `admin` or `staff`. Response `200`: `{ "member": { ... } }`. Errors: `404`.

### POST /api/elderly
- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "full_name": "string, required, max 150",
    "gender": "Male | Female | Other, required",
    "date_of_birth": "YYYY-MM-DD, optional",
    "location": "string, optional, max 150",
    "opa_id": "integer, optional — must reference an existing OPA",
    "emergency_contact_name": "string, optional, max 120",
    "emergency_contact_phone": "string, optional, max 40",
    "emergency_contact_relationship": "string, optional, max 60",
    "vulnerability_notes": "string, optional, max 4000",
    "health_notes": "string, optional, max 4000",
    "allergies": "string, optional, max 2000",
    "dietary_requirements": "string, optional, max 2000",
    "status": "Active | Inactive | Deceased | Transferred, optional, default Active"
  }
  ```
- **Response `201`:** `{ "member": { ... } }`
- **Errors:** `400` validation (includes an unknown `opa_id`).

### PATCH /api/elderly/{id}
- **Auth:** `admin` or `staff`. Partial subset of the create fields. Response `200`: `{ "member": { ... } }`. Errors: `400`, `404`.

### DELETE /api/elderly/{id}
- **Auth:** `admin` only (stricter than the rest of this module — deleting a person record is meant to correct a mistaken entry, not routine offboarding; prefer `PATCH status` to `Inactive`/`Transferred`/`Deceased` instead). Response `204`. Errors: `404`.

## GET /api/elderly/{id}/timeline — Care Timeline

Combines events from 7 existing modules into one chronological feed for
one person — **not** a new event table duplicating those records.
Deliberately not built that way: every event here already lives in its
own module's table (`Attendance`, `HealthRecord`,
`MedicationAdministration`, `HomeVisit`, `AssistanceRequest`, `Incident`,
`MealAttendance`); this endpoint queries all 7, scoped to one
`elderly_member_id`, and merges + sorts the results. That's exactly 7
fixed, already-indexed queries — not N+1 (N would scale with the amount
of history; this never does) — plus one batch lookup for photo
attachments (a single `IN` query, not one per visit/request).

- **Auth:** `admin` or `staff`.
- **Query params (optional):** `page` (default 1), `per_page` (default 20, max 100).
- **Response `200`:**
  ```json
  {
    "member": { ...full elderly member object... },
    "timeline": [
      {
        "type": "home_visit", "timestamp": "2026-08-24T10:00:00+00:00", "title": "Home Visit",
        "details": { "assigned_to": "Grace Mwangi", "status": "Completed", "reason": "...", "observations": "...", "has_photo": true }
      }
    ],
    "pagination": { "page": 1, "per_page": 20, "total": 12, "pages": 1 }
  }
  ```
  `type` is one of `attendance | health | medication | home_visit | assistance | incident | meal`. `details` shape varies by type — always includes whatever's meaningful for that event (see `elderly/routes.py`'s `get_member_timeline`), never the full source record. Newest first.
- **Errors:** `403`, `404`.
