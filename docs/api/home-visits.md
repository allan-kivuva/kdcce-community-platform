# Home visits

`backend/app/homevisits/` — visit requests for elderly members who can't
(or don't) come to the centre. Depends on [elderly.md](elderly.md) and
[volunteers.md](volunteers.md) (assignment requires a verified volunteer).

This is the one module with real per-user scoping, not just role-gating:
a `volunteer` token only ever sees/edits visits assigned to them, and only
a restricted set of fields (the outcome, not the assignment). `admin`/
`staff` see and can edit everything.

Home visit object:
```json
{
  "id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng",
  "elderly_member_code": "KDCCE-2026-0001", "requested_by": "Jane Staffer",
  "assigned_to_id": 4, "assigned_to": "Grace Mwangi",
  "priority": "High", "status": "Assigned",
  "reason": "Unable to attend the centre due to mobility issues",
  "scheduled_at": null, "completed_at": null,
  "observations": null, "support_provided": null,
  "follow_up_required": false, "follow_up_notes": null,
  "created_at": "...", "updated_at": "..."
}
```

Priorities: `Low | Medium | High | Urgent` (default `Medium`).
Statuses: `Pending | Assigned | Scheduled | In Progress | Completed | Cancelled`
— there's no enforced state machine; admin/staff (and the assignee, within
their allowed fields) can set any status directly. Setting `status` to
`Completed` stamps `completed_at` server-side the first time it happens.

## GET /api/home-visits/assignees

Who a visit can be assigned to: every `admin`/`staff` user, plus every
volunteer whose profile status is `Verified` (never a `Pending`/`Rejected`
one). Purpose-built for the assignment dropdown — there's no general
user-listing endpoint in this app.

- **Auth:** `admin` or `staff`.
- **Response `200`:** `{ "assignees": [ { "id": 4, "name": "Grace Mwangi", "role": "volunteer" }, ... ] }`

## POST /api/home-visits

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "elderly_member_id": "integer, required",
    "reason": "string, required, max 2000",
    "priority": "Low | Medium | High | Urgent, optional, default Medium",
    "assigned_to_id": "integer, optional — must be staff/admin or a Verified volunteer",
    "scheduled_at": "ISO datetime, optional"
  }
  ```
  `status` is not accepted here — it's always `Pending`, or `Assigned` if `assigned_to_id` was given.
- **Response `201`:** `{ "visit": { ... } }`
- **Errors:** `400` validation (unknown `elderly_member_id`, or `assigned_to_id` that isn't staff/admin/verified-volunteer).

## GET /api/home-visits

- **Auth:** any authenticated user.
  - `admin`/`staff`: see everything. Query params (optional): `status`, `priority`, `elderly_member_id`, `assigned_to_id`.
  - `volunteer`: **always scoped to their own assigned visits** regardless of `assigned_to_id` — `status`/`priority` filters still apply on top of that.
- **Response `200`:** `{ "visits": [ { ... }, ... ] }`, newest first.

## GET /api/home-visits/{id}
- **Auth:** `admin`/`staff` see any visit. A `volunteer` gets `403` unless `assigned_to_id` is their own user id.
- **Response `200`:** `{ "visit": { ... } }`. Errors: `403`, `404`.

## PATCH /api/home-visits/{id}

Two different bodies depending on who's asking — same endpoint.

- **`admin`/`staff`:** any subset of `elderly_member_id`, `assigned_to_id`, `priority`, `status`, `reason`, `scheduled_at`, `observations`, `support_provided`, `follow_up_required`, `follow_up_notes`.
- **The assigned volunteer/staff member on their own visit:** only `status`, `observations`, `support_provided`, `follow_up_required`, `follow_up_notes` — sending `elderly_member_id`, `assigned_to_id`, `priority`, `reason`, or `scheduled_at` is rejected as an unknown field (`400`), not silently dropped.
- **Anyone else** (a volunteer on a visit not assigned to them): `403`.
- Omitted fields are left unchanged in both cases — never reset to a default (in particular, omitting `status` never resets it to `Pending`).
- **Response `200`:** `{ "visit": { ... } }`. Errors: `400`, `403`, `404`.

## DELETE /api/home-visits/{id}
- **Auth:** `admin` only. Response `204`. Errors: `404`.
