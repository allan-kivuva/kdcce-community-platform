# Team

`backend/app/team/` — public "meet the team" bios. This is marketing-site
content (name/role/photo), not an operational staff/caregiver record — see
the roadmap note in the repo root README about a future, separate
caregiver/volunteer profile model.

Team member object:
```json
{ "id": 1, "name": "...", "role": "Program Coordinator", "image": "/images/team-derrick.jpg", "created_at": "...", "updated_at": "..." }
```

## GET /api/team

- **Auth:** none.
- **Response `200`:** `{ "team": [ { ... }, ... ] }`, oldest first (registration order).

## POST /api/admin/team

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  { "name": "string, required, max 120", "role": "string, required, max 120", "image": "string, required, max 500" }
  ```
- **Response `201`:** `{ "member": { ... } }`
- **Errors:** `400` validation.

## PATCH /api/admin/team/{id}

- **Auth:** `admin` or `staff`.
- **Request:** any subset of `name`, `role`, `image` (partial).
- **Response `200`:** `{ "member": { ... } }`
- **Errors:** `400` validation, `404`.

## DELETE /api/admin/team/{id}

- **Auth:** `admin` or `staff`.
- **Response `204`:** no body.
- **Errors:** `404`.
