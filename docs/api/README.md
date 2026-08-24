# API contract

Source of truth for what the backend exposes and what the frontend can rely
on. Update the relevant file here in the same PR that changes an endpoint —
frontend developers should never need to read Flask route code to know a
request/response shape.

Base URL: `http://localhost:5000` in dev (`VITE_API_URL` on the frontend
side). All request/response bodies are JSON unless noted.

## Auth

Protected endpoints require `Authorization: Bearer <access_token>`. Get a
token from [`auth.md`](auth.md). Access tokens expire after 1 hour; use
`POST /api/auth/refresh` with the refresh token (30-day expiry) to get a new
one. Roles today: `admin`, `staff`, `volunteer` — a route documented as
"admin, staff" rejects a `volunteer` token with `403`.

## Standard error shape

Every non-2xx response is `{ "error": "<message>" }`, plus `"details"` for
validation failures:

| Status | Meaning | Body |
|---|---|---|
| 400 | Validation failed | `{ "error": "Validation failed", "details": { "<field>": ["<message>"] } }` |
| 401 | Missing/invalid/expired/revoked token | `{ "error": "Authentication required" \| "Invalid or expired token" \| "Token has expired" \| "Token has been revoked" }` |
| 403 | Authenticated but wrong role | `{ "error": "Forbidden" }` |
| 404 | Resource not found | `{ "error": "<Model> not found" }` |
| 409 | Conflict (e.g. duplicate email) | `{ "error": "<message>" }` |

A `204 No Content` response (deletes) has no body.

## Security

Every response carries `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
`Content-Security-Policy: default-src 'none'` (safe to lock all the way down
— this API only ever returns JSON, never HTML), and
`Strict-Transport-Security` (a no-op over plain HTTP in dev; takes effect
once served over HTTPS). See `app/__init__.py`'s `_security_headers`.

Logout revokes tokens server-side rather than only clearing them
client-side — see [`auth.md`](auth.md#post-apiauthlogout). Every public,
unauthenticated write endpoint (`register`, `login`, `POST /api/donations`,
`POST /api/inbox`) is rate-limited to 10/minute per IP.

## Modules

| Module | Doc | Status |
|---|---|---|
| Auth | [auth.md](auth.md) | Implemented |
| Elderly members & OPAs | [elderly.md](elderly.md) | Implemented |
| Attendance | [attendance.md](attendance.md) | Implemented |
| Health & wellness | [health.md](health.md) | Implemented |
| Medication | [medication.md](medication.md) | Implemented |
| Volunteers | [volunteers.md](volunteers.md) | Implemented |
| Home visits | [home-visits.md](home-visits.md) | Implemented |
| Feeding | [feeding.md](feeding.md) | Implemented |
| Inventory | [inventory.md](inventory.md) | Implemented |
| Activities | [activities.md](activities.md) | Implemented |
| Assistance requests | [assistance.md](assistance.md) | Implemented |
| Incidents | [incidents.md](incidents.md) | Implemented |
| Reports | [reports.md](reports.md) | Implemented |
| Analytics | [analytics.md](analytics.md) | Implemented |
| Notifications | [notifications.md](notifications.md) | Implemented |
| Inbox | [inbox.md](inbox.md) | Implemented |
| Assignment photo & conversation | [assignment-collaboration.md](assignment-collaboration.md) | Implemented |
| Follow-ups | [followups.md](followups.md) | Implemented |
| Assignment calendar | [calendar.md](calendar.md) | Implemented |
| Global search | [search.md](search.md) | Implemented |
| Donations | [donations.md](donations.md) | Implemented |
| Blog | [blog.md](blog.md) | Implemented |
| Gallery | [gallery.md](gallery.md) | Implemented |
| Crafts | [crafts.md](crafts.md) | Implemented |
| Team | [team.md](team.md) | Implemented |
| Clinic/medical visits | — | Not built yet — add a doc file here as each module lands |
