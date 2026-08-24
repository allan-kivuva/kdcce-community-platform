# Auth

`backend/app/auth/` — JSON Web Token auth. Public self-registration always
creates a `volunteer`; there is no client-controlled way to get a higher
role (an admin must be promoted directly in the database for now — no
"promote user" endpoint exists yet).

## POST /api/auth/register

- **Auth:** none. Rate-limited: 10/min per IP.
- **Request:**
  ```json
  { "name": "Grace Mwangi", "email": "grace@example.com", "password": "at-least-8-chars" }
  ```
- **Response `201`:**
  ```json
  {
    "user": { "id": 1, "name": "Grace Mwangi", "email": "grace@example.com", "role": "volunteer", "created_at": "2026-08-24T10:00:00+00:00" },
    "access_token": "...",
    "refresh_token": "..."
  }
  ```
- **Errors:** `400` validation (`name` required, `email` must be valid, `password` min length 8); `409` if the email is already registered.

## POST /api/auth/login

- **Auth:** none. Rate-limited: 10/min per IP.
- **Request:** `{ "email": "...", "password": "..." }`
- **Response `200`:** same shape as register.
- **Errors:** `400` validation; `401` wrong email/password (message doesn't reveal which).

## POST /api/auth/refresh

- **Auth:** `Authorization: Bearer <refresh_token>` (not the access token).
- **Response `200`:** `{ "access_token": "..." }`
- **Errors:** `401` if given an access token instead of a refresh token, or if expired/invalid.

## GET /api/auth/me

- **Auth:** `Authorization: Bearer <access_token>`, any role.
- **Response `200`:** `{ "user": { "id": ..., "name": ..., "email": ..., "role": ..., "created_at": ... } }`
- **Errors:** `401` missing/invalid/expired token.

## Frontend usage

`frontend/src/lib/api.js` — `apiFetch()` attaches the stored access token
automatically. `setSession(token, user)` / `getStoredUser()` / `clearSession()`
manage `localStorage`. On any `401`, calling code should `clearSession()` and
redirect to `/admin/login` (see `useApiResource` in `AdminDashboard.jsx` for
the pattern to reuse in new modules).
