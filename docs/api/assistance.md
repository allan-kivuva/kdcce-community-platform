# Assistance requests

`backend/app/assistance/` — the request → matching → assignment →
acceptance → in-progress → completion lifecycle. Depends on
[elderly.md](elderly.md) and [volunteers.md](volunteers.md)
(`assigned_to_id` follows the exact same rule as `HomeVisit.assigned_to_id`
— see [home-visits.md](home-visits.md) — staff/admin or a `Verified`
volunteer only) and optionally links to a [home visit](home-visits.md).

Like home visits, this has real per-user scoping: a `volunteer` token
only ever sees/edits requests assigned to them, and only a restricted
outcome field set. `admin`/`staff` see and can edit everything.

Same current-status gate as home visits (see
[volunteers.md](volunteers.md#portal-access-gate)): a volunteer also needs
`VolunteerProfile.status == "Verified"` right now, checked fresh on every
request — including `POST .../accept` — not just "is this assigned to
me," since rejection doesn't retroactively clear existing assignments.

**Acceptance is not just another status a PATCH can set.** It's its own
endpoint (`POST .../accept`) callable only by the assigned user, on their
own request, only while it's `Assigned`. This is the one meaningful
difference from home visits — the brief specifically calls out
"Acceptance" as its own lifecycle step, so it isn't folded into the
generic status field the way every other module's lifecycle is.

Request object:
```json
{
  "id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng",
  "elderly_member_code": "KDCCE-2026-0001", "requested_by": "Jane Staffer",
  "assigned_to_id": 4, "assigned_to": "Grace Mwangi", "home_visit_id": null,
  "request_type": "Companionship", "priority": "Medium", "status": "Accepted",
  "description": "Would like a weekly visitor",
  "scheduled_at": null, "completed_at": null, "outcome_notes": null,
  "follow_up_required": false, "follow_up_notes": null,
  "created_at": "...", "updated_at": "..."
}
```
`request_type`: `Hospital Accompaniment | Transportation | Food Assistance
| Companionship | Home Support | Other`. `priority`: `Low | Medium | High
| Urgent`. `status`: `Requested | Matching | Assigned | Accepted | In
Progress | Completed | Cancelled` — no enforced transitions between these
(same as every other lifecycle module) except `Accepted`, which is only
reachable via the accept endpoint below.

`follow_up_required`/`follow_up_notes` — added alongside `HealthRecord`,
`HomeVisit`, and `Incident`'s identical pair, so an assistance request can
originate a follow-up the same way those 3 already could. **`true`
auto-creates a [FollowUp](followups.md)** (defaulting `assigned_to_id` to
this request's own assignee, if any) on a `False → True` `PATCH`. Not
settable at creation.

## POST /api/assistance-requests

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "elderly_member_id": "integer, required",
    "request_type": "required, see above",
    "description": "string, required, max 2000",
    "priority": "optional, default Medium",
    "assigned_to_id": "integer, optional — staff/admin or a Verified volunteer",
    "home_visit_id": "integer, optional — must reference an existing home visit",
    "scheduled_at": "ISO datetime, optional"
  }
  ```
  `status` is not accepted — always `Requested`, or `Assigned` if `assigned_to_id` was given.
- **Response `201`:** `{ "request": { ... } }`
- **Errors:** `400` validation (unknown member, invalid assignee, unknown home visit).

## GET /api/assistance-requests

- **Auth:** any authenticated user.
  - `admin`/`staff`: everything. Query params (optional): `status`, `priority`, `request_type`, `elderly_member_id`, `assigned_to_id`.
  - `volunteer`: **always scoped to their own assigned requests**, `status`/`priority`/`request_type` filters still apply on top.
- **Response `200`:** `{ "requests": [ { ... }, ... ] }`, newest first.

## GET /api/assistance-requests/{id}
- `admin`/`staff` see any; a `volunteer` gets `403` unless it's assigned to them. Errors: `403`, `404`.

## PATCH /api/assistance-requests/{id}

- **`admin`/`staff`:** any subset of `elderly_member_id`, `assigned_to_id`, `home_visit_id`, `request_type`, `priority`, `status`, `description`, `scheduled_at`, `outcome_notes`, `follow_up_required`, `follow_up_notes`.
- **The assigned volunteer/staff member on their own request:** only `status` (restricted to `In Progress | Completed | Cancelled` — not `Accepted`, not the staff-only states), `outcome_notes`, `follow_up_required`, `follow_up_notes`. Sending anything else, including `status: "Accepted"`, is rejected as invalid/unknown (`400`).
- **Anyone else:** `403`.
- Omitted fields are left unchanged, never reset. Setting `status` to `Completed` stamps `completed_at` the first time it happens.
- **Errors:** `400`, `403`, `404`.

## POST /api/assistance-requests/{id}/accept

- **Auth:** must be this request's `assigned_to_id`.
- **Response `200`:** `{ "request": { ... } }`, `status` now `Accepted`.
- **Errors:** `403` if you're not the assignee (including when nobody is assigned yet); `409` if the request isn't currently `Assigned` (e.g. already accepted, or still unassigned).

## DELETE /api/assistance-requests/{id}
- **Auth:** `admin` only. Errors: `404`.

## Photo and private conversation

Identical mechanism and endpoint shapes as home visits — see
[home-visits.md](home-visits.md#photo-and-private-conversation) and
[assignment-collaboration.md](assignment-collaboration.md) for the full
design. Same access rule as this request itself (`_can_access_request`):

```
POST /api/assistance-requests/{id}/photo       multipart/form-data, field "photo"
GET  /api/assistance-requests/{id}/photo
GET  /api/assistance-requests/{id}/messages
POST /api/assistance-requests/{id}/messages    { "body": "..." }
```

## Admin review (star rating)

Same mechanism as home visits — see
[home-visits.md](home-visits.md#admin-review-star-rating). `POST` requires
`admin` (not staff) and `status == "Completed"` (`409` otherwise); `GET`
uses `_can_access_request`.

```
POST /api/assistance-requests/{id}/review   { "rating": 1-5, "comment": "optional" }
GET  /api/assistance-requests/{id}/review
```
