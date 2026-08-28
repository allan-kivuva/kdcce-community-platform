# Inbox

`backend/app/inbox/` — the public contact-form pipeline: visitors submit
through the site's Contact page, staff/admin triage in a shared inbox.

**Not identity-scoped** — unlike [Notifications](notifications.md), an
`InboxMessage` has no owner. Any `admin`/`staff` can view, mark read/unread,
or delete any message; the sender is a public visitor, not a `User` row.
This is a deliberate difference from Notification's per-recipient model:
Inbox is a shared team mailbox, not a private feed.

Two blueprints at different URL prefixes (same pattern as
`donations`/`admin_donations`): `POST /api/inbox` is public; every other
endpoint is `/api/admin/inbox` and staff/admin-only.

Message object:
```json
{
  "id": 1, "name": "Grace M.", "email": "grace@example.com",
  "subject": "Volunteering interest", "message": "Hi, I would love to...",
  "is_read": false, "created_at": "..."
}
```

## POST /api/inbox
- **Auth:** none — the public contact form. Rate-limited to 10/minute per
  IP (same defense as `auth`'s public endpoints — a text form is a typical
  spam-bot target).
- **Request:** `{ "name", "email", "subject", "message" }`, all required.
  `is_read` is never accepted from the client — always `false` at creation.
- **Response `201`:** `{ "message": { ... } }`.

## GET /api/admin/inbox
- **Auth:** `admin`, `staff`.
- **Query params (optional):** `unread_only` (`true`), `page` (default 1),
  `per_page` (default 20, max 100).
- **Response `200`:** `{ "messages": [...], "pagination": { "page", "per_page", "total", "pages" } }`, newest first.

## PATCH /api/admin/inbox/{id}
- **Auth:** `admin`, `staff`.
- **Request:** `{ "is_read": true | false }` — the only mutable field.
- **Response `200`:** `{ "message": { ... } }`. **Errors:** `404` if missing.

## DELETE /api/admin/inbox/{id}
- **Auth:** `admin`, `staff`. Response `204`. Errors: `404` if missing.
