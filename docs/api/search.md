# Global search

`backend/app/search/` — a single query across elderly members, volunteers,
home visits, assistance requests, and follow-ups.

**`admin`/`staff` only, no volunteer access at all.** A volunteer has no
elderly-record access anywhere else in this app (see `elderly.md`,
`incidents.md`'s model docstring) — a search spanning elderly members
would be a new leak, not a convenience. A volunteer's own assignment
lists (`My Home Visits`, `My Assistance Requests`) are already small
enough not to need search.

## GET /api/search
- **Auth:** `admin`, `staff`.
- **Query params:** `q` (required, min 2 characters) — case-insensitive substring match (`ILIKE`) against: elderly member name/member ID, volunteer name/email, home visit / assistance request elderly-member name, follow-up elderly-member name/reason.
- **Response `200`:**
  ```json
  {
    "results": {
      "elderly_members": [ {...full elderly member object, up to 5} ],
      "volunteers": [ {...full volunteer profile object, up to 5} ],
      "home_visits": [ {...full home visit object, up to 5} ],
      "assistance_requests": [ {...full assistance request object, up to 5} ],
      "follow_ups": [ {...full follow-up object, up to 5} ]
    }
  }
  ```
  Each category capped at 5 results — this is a quick-jump search, not a
  paginated report (use the relevant module's own list endpoint, or
  `/api/reports/*`, for exhaustive results).
- **Errors:** `400` if `q` is missing or under 2 characters; `403`; `401`.
