# Auth

`backend/app/auth/` — JSON Web Token auth. Public self-registration always
creates a `volunteer`; there is no client-controlled way to get a higher
role (an admin must be promoted directly in the database for now — no
"promote user" endpoint exists yet).

**Revocation:** every access/refresh token carries a `jti`; logging out adds
it to `RevokedToken` (`backend/app/models.py`), checked on every
`@jwt_required()` route via `jwt.token_in_blocklist_loader`
(`backend/app/__init__.py`). Without this a token stays valid for its full
lifetime (1h access / 30d refresh) with no way to kill it early — logout
would otherwise only ever be a client-side `localStorage` clear. Revoked
rows are never pruned (no scheduler exists in this codebase); a row past its
token's original expiry is just inert, unpruned storage, not a correctness
issue.

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

This is also the first step of the public "Become a Volunteer" flow
(`frontend/src/pages/BecomeAVolunteer.jsx`) — it's the same endpoint,
not a separate one. The page follows this call immediately with
`PATCH /api/volunteers/me` to fill in the rest of the application; see
[volunteers.md](volunteers.md).

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

## POST /api/auth/logout

- **Auth:** `Authorization: Bearer <access_token>`.
- **Request (optional body):** `{ "refresh_token": "..." }` — if provided and
  it decodes as a genuine refresh token, it's revoked too in the same call.
  An unparseable value, or a token whose `type` claim isn't `"refresh"`
  (e.g. an access token passed here by mistake), is silently ignored rather
  than erroring — the access token used to authenticate this request is
  still revoked either way.
- **Response `204`.** From this point on, both tokens are rejected by every
  protected route with `401 { "error": "Token has been revoked" }`, even
  though neither has naturally expired yet.

## Frontend usage

`frontend/src/lib/api.js` — `apiFetch()` attaches the stored access token
automatically. `setSession(token, user, refreshToken)` / `getStoredUser()` /
`getToken()` / `getRefreshToken()` manage `localStorage`. Two ways to end a
session:
- **User-initiated sign-out:** call `endSession()` — it calls
  `POST /api/auth/logout` (revoking both tokens server-side) and then clears
  `localStorage` regardless of whether that call succeeds, so signing out
  locally is never blocked by a network failure. Used by `Shell.jsx`'s
  sign-out button.
- **A `401` from any other request** (token already invalid/expired): call
  `clearSession()` directly, not `endSession()` — there's nothing left to
  revoke, so skip the extra network round-trip. See `useApiResource`'s `load`
  for the pattern to reuse in new modules.
