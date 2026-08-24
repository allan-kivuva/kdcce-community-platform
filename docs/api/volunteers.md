# Volunteers

`backend/app/volunteers/` — the extra profile data for a `User` with
`role='volunteer'` (skills, availability, verification). Not every `User`
row has one — only volunteers — but every volunteer gets one automatically:
`POST /api/auth/register` always creates a `volunteer`-role user, and
creates a matching `VolunteerProfile` (status `Pending`) in the same
transaction. There is no manual "register a volunteer" endpoint for staff;
self-signup is the only path in, same as for `User` itself.

Assignment history and hours worked are **not** stored here — they'll be
derived from home-visit/activity records once those modules exist, not
duplicated.

Volunteer profile object:
```json
{
  "id": 1, "user_id": 4, "name": "Grace Mwangi", "email": "grace@example.com",
  "phone": "0712345678", "skills": "Cooking, first aid", "availability": "Weekday mornings",
  "bio": "Retired nurse, lives in Kibera.", "status": "Verified",
  "reviewed_by": "Jane Staffer", "reviewed_at": "2026-08-24T10:00:00+00:00",
  "created_at": "...", "updated_at": "..."
}
```

## Self-service (any authenticated user with a profile)

### GET /api/volunteers/me
- **Auth:** any valid token. Response `200`: `{ "volunteer": { ... } }`. Errors: `401`; `404` if this account has no volunteer profile (e.g. an admin/staff account).

### PATCH /api/volunteers/me
- **Auth:** any valid token with a profile.
- **Request:** any subset of `{ "phone", "skills", "availability", "bio" }` (all optional strings) — **`status` is not accepted here**, sending it is rejected as an unknown field (`400`). Omitted fields are left unchanged, never reset.
- **Response `200`:** `{ "volunteer": { ... } }`. Errors: `400`, `401`, `404`.

## Staff management

### GET /api/volunteers
- **Auth:** `admin` or `staff`.
- **Query params (optional):** `status` (`Pending` | `Verified` | `Rejected`).
- **Response `200`:** `{ "volunteers": [ { ... }, ... ] }`, newest first.

### GET /api/volunteers/{id}
- **Auth:** `admin` or `staff`. Response `200`: `{ "volunteer": { ... } }`. Errors: `404`.

### PATCH /api/volunteers/{id}
- **Auth:** `admin` or `staff`.
- **Request:** any subset of the self-service fields plus `status` (`Pending` | `Verified` | `Rejected`). Changing `status` to a different value stamps `reviewed_by`/`reviewed_at` with the acting admin/staff user and the current time — regardless of which direction the change goes (Verified→Rejected counts too). Omitted fields are left unchanged, never reset (in particular, omitting `status` does not reset it to `Pending`).
- **Response `200`:** `{ "volunteer": { ... } }`. Errors: `400`, `404`.
