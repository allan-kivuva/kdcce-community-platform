# Home visits

`backend/app/homevisits/` — visit requests for elderly members who can't
(or don't) come to the centre. Depends on [elderly.md](elderly.md) and
[volunteers.md](volunteers.md) (assignment requires a verified volunteer).

This is the one module with real per-user scoping, not just role-gating:
a `volunteer` token only ever sees/edits visits assigned to them, and only
a restricted set of fields (the outcome, not the assignment). `admin`/
`staff` see and can edit everything.

A volunteer's access additionally requires their **current**
`VolunteerProfile.status == "Verified"` (see [volunteers.md](volunteers.md#portal-access-gate))
— checked fresh on every request, not just at assignment time. A visit's
`assigned_to_id` isn't cleared if that volunteer is later rejected, so
relying only on "is this visit assigned to me" would leave a rejected
volunteer with access to visits from before their rejection.

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

**`follow_up_required: true` auto-creates a [FollowUp](followups.md)**
(defaulting `assigned_to_id` to this visit's own assignee, if any) — on a
`PATCH` that transitions it `False → True`. Not settable at creation —
see `POST` below.

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

## Photo and private conversation

`backend/app/assignments/` — an optional photo and a private volunteer↔
staff message thread on a visit, added alongside (not replacing) the
outcome fields above. Access to both is exactly the same rule as the
visit itself — see `_can_access_visit` in `routes.py`: `admin`/`staff`
always, or the assigned user while currently `Verified`; nobody else.
Full design rationale (why this isn't the Phase 7D public contact Inbox,
why the photo is never a public URL, file validation approach) is in
[assignment-collaboration.md](assignment-collaboration.md) — this section
just documents the endpoint shapes.

### POST /api/home-visits/{id}/photo
- **Auth:** same as above. `multipart/form-data`, field name `photo`. JPEG/PNG/WebP only (verified from the file's own bytes, not the filename or client Content-Type), max 5MB.
- At most one photo per visit — uploading again replaces the previous one.
- **Response `201`:** `{ "attachment": { "id", "original_filename", "mime_type", "file_size", "uploaded_by", "created_at" } }`.
- **Errors:** `400` (`{"error": "Validation failed", "details": {"photo": [...]}}` — missing/wrong type/too large), `403`, `404`.

### GET /api/home-visits/{id}/photo
- **Auth:** same as above. Streams the file directly (`Content-Type` is the server-verified MIME type). There is no other way to reach this file — no public static path exists for it.
- **Errors:** `404` if no photo has been uploaded (or the visit doesn't exist), `403`, `401`.

### GET /api/home-visits/{id}/messages
- **Auth:** same as above. **Response `200`:** `{ "messages": [ { "id", "sender_id", "sender_name", "body", "created_at" }, ... ] }`, oldest first.

### POST /api/home-visits/{id}/messages
- **Auth:** same as above. **Request:** `{ "body": "string, required, max 4000" }`.
- Notifies the other party via the existing notification system (`Assignment Message`): the volunteer's message notifies whoever requested the visit; a staff/admin message notifies the assigned volunteer.
- **Response `201`:** `{ "message": { ... } }`. Errors: `400`, `403`, `404`.

## Admin review (star rating)

`AssignmentReview` — a 1-5 star rating plus an optional comment on how
the assigned volunteer/staff member handled a **Completed** visit.
**Admin only to submit** — deliberately not the usual `("admin", "staff")`
pair used everywhere else in this module. Viewing uses the same access
rule as the visit itself (`_can_access_visit`), so the reviewed volunteer
can see their own feedback. At most one review per assignment —
submitting again replaces it, same "create or replace" behavior as the
photo above. Full design rationale in
[assignment-collaboration.md](assignment-collaboration.md).

### POST /api/home-visits/{id}/review
- **Auth:** `admin` only. Requires the visit's `status` to already be `Completed` — `409` otherwise.
- **Request:** `{ "rating": "integer 1-5, required", "comment": "string, optional, max 2000" }`.
- Notifies the assigned volunteer/staff (`Assignment Reviewed`, title includes a `★`/`☆` rendering of the rating) via the existing `notify()`.
- **Response `201`:** `{ "review": { "id", "rating", "comment", "reviewed_by", "created_at", "updated_at" } }`. Errors: `400`, `403`, `404`, `409`.

### GET /api/home-visits/{id}/review
- **Auth:** same access rule as the visit itself (`admin`/`staff`, or the assigned user while currently `Verified`).
- **Response `200`:** `{ "review": { ... } }`. Errors: `403`, `404` (no review yet, or the visit doesn't exist).
