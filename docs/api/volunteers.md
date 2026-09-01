# Volunteers

`backend/app/volunteers/` — the extra profile data for a `User` with
`role='volunteer'` (skills, availability, verification). Not every `User`
row has one — only volunteers — but every volunteer gets one automatically:
`POST /api/auth/register` always creates a `volunteer`-role user, and
creates a matching `VolunteerProfile` (status `Pending`) in the same
transaction. There is no manual "register a volunteer" endpoint for staff;
self-signup is the only path in, same as for `User` itself.

**`VolunteerProfile` IS the volunteer application** — there is no separate
`VolunteerApplication` model. It already carried `status`
(`Pending`/`Verified`/`Rejected`), `reviewed_by`, `reviewed_at`, and
`created_at` (doubling as "submitted at"); a second model would just
duplicate that bookkeeping. The public "Become a Volunteer" flow
(`frontend/src/pages/BecomeAVolunteer.jsx`) is two calls against existing
endpoints, not a new one: `POST /api/auth/register` (creates the account),
then this module's `PATCH /me` (fills in the rest of the application).
"Approved" in product language is the existing `Verified` status — it
wasn't renamed, to avoid an invasive change across an already-tested
system.

Assignment history and hours worked are **not** stored here — they're
derived from home-visit/activity records, not duplicated.

Volunteer profile object:
```json
{
  "id": 1, "user_id": 4, "name": "Grace Mwangi", "email": "grace@example.com",
  "phone": "0712345678", "skills": "Cooking, first aid", "availability": "Weekday mornings",
  "areas_of_interest": "Home visits, feeding program", "experience": "Two years at a local shelter",
  "motivation": "I want to give back", "bio": "Retired nurse, lives in Kibera.",
  "status": "Verified", "rejection_reason": null,
  "reviewed_by": "Jane Staffer", "reviewed_at": "2026-08-24T10:00:00+00:00",
  "created_at": "...", "updated_at": "..."
}
```

## Portal access gate

A volunteer's access to their own assignment data (`GET`/`PATCH` on
`/api/home-visits` and `/api/assistance-requests`, plus
`POST .../accept`) requires `status == "Verified"` **at request time**,
checked directly against the database — not inferred from whether the
visit/request happens to be assigned to them. This matters because
rejecting a volunteer does not retroactively clear their existing
assignments: without this explicit check, a volunteer who was verified,
assigned work, and later rejected would keep access to it. `GET`/`PATCH
/api/volunteers/me` and `/api/notifications` are **not** gated this way —
a Pending or Rejected applicant must still be able to see their own
application status and their approval/rejection notification.

## Self-service (any authenticated user with a profile)

### GET /api/volunteers/me
- **Auth:** any valid token. Response `200`: `{ "volunteer": { ... } }`. Errors: `401`; `404` if this account has no volunteer profile (e.g. an admin/staff account).

### PATCH /api/volunteers/me
- **Auth:** any valid token with a profile. Used both for the initial application (immediately after registration) and for later self-service edits — same fields either way.
- **Request:** any subset of `{ "phone", "skills", "availability", "areas_of_interest", "experience", "motivation", "bio" }` (all optional strings) — **`status` and `rejection_reason` are not accepted here**, sending either is rejected as an unknown field (`400`), which also means a payload mixing a legitimate field with `status` 400s as a whole rather than silently applying the legitimate part. Omitted fields are left unchanged, never reset.
- **Response `200`:** `{ "volunteer": { ... } }`. Errors: `400`, `401`, `404`.

## Structured availability (self-service)

Alongside the free-text `availability` field on the profile itself, a
volunteer can also record structured, queryable availability — recurring
weekly windows and specific unavailable date ranges. Both are purely
informational for admin/staff to consult when assigning work: nothing
validates or blocks assignment creation against them (that's a future
matching feature, not this one). The free-text field is unchanged and
independent — a volunteer may use either, both, or neither.

### GET /api/volunteers/me/availability
- **Auth:** any valid token with a profile. Response `200`: `{ "availability": [ { "id": 1, "day_of_week": "Monday", "start_time": "09:00", "end_time": "12:00" }, ... ] }`.

### POST /api/volunteers/me/availability
- **Request:** `{ "day_of_week": "Monday" (one of Monday..Sunday), "start_time": "09:00", "end_time": "12:00" }` — `end_time` must be after `start_time` (`400` otherwise).
- **Response `201`:** `{ "availability": { ... } }`.

### DELETE /api/volunteers/me/availability/{id}
- Removes one of your own windows. `404` (not `403`) if the id isn't yours — same anti-enumeration shape used elsewhere in this app.

### GET /api/volunteers/me/unavailability
- Same shape, for date-range exceptions: `{ "unavailability": [ { "id": 1, "start_date": "2026-12-20", "end_date": "2027-01-05", "reason": "Holiday travel" }, ... ] }`. `reason` is optional.

### POST /api/volunteers/me/unavailability
- **Request:** `{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "reason": "optional string, max 200" }` — `end_date` must not be before `start_date`.

### DELETE /api/volunteers/me/unavailability/{id}
- Same ownership/404 rule as the availability delete above.

## Staff management

### GET /api/volunteers
- **Auth:** `admin` or `staff`.
- **Query params (optional):** `status` (`Pending` | `Verified` | `Rejected`).
- **Response `200`:** `{ "volunteers": [ { ... }, ... ] }`, newest first.

### GET /api/volunteers/{id}
- **Auth:** `admin` or `staff`. Response `200`: `{ "volunteer": { ... } }`. Errors: `404`.

### GET /api/volunteers/{id}/availability
- **Auth:** `admin` or `staff` — read-only, for consulting a volunteer's offered windows when deciding who to assign work to. There is no admin/staff write path here on purpose (a volunteer's own statement of when they're free isn't something staff edit for them). Response `200`: `{ "availability": [ ... ], "unavailability": [ ... ] }` (same shapes as the self-service endpoints above). Errors: `404`.

### PATCH /api/volunteers/{id}
- **Auth:** `admin` or `staff`.
- **Request:** any subset of the self-service fields plus `status` (`Pending` | `Verified` | `Rejected`) and `rejection_reason` (optional string, shown to the applicant in their rejection notification — not an internal-only note). Changing `status` to a different value stamps `reviewed_by`/`reviewed_at` with the acting admin/staff user and the current time, and fires a notification: `Volunteer Verified` on approval, `Volunteer Rejected` (including `rejection_reason` in the message, if given) on rejection. Setting `status` to anything other than `Rejected` clears any previously-set `rejection_reason`, so a reason from an earlier rejection can't resurface attached to a later, different decision. Omitted fields are left unchanged, never reset (in particular, omitting `status` does not reset it to `Pending`).
- **Response `200`:** `{ "volunteer": { ... } }`. Errors: `400`, `404`.
