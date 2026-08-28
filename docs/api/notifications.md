# Notifications

`backend/app/notifications/` — in-app notifications. One `Notification` row
per (event, recipient), not a separate `Notification`/`NotificationRecipient`
pair: every type here is inherently single-recipient in this system (an
assignment, a personal alert); a rare broadcast (a low-stock alert to every
admin/staff) just costs a handful of duplicate rows, cheap at this
system's scale and simpler than a fan-out join table this system's actual
usage never needs.

**Authorization is identity-scoped, not role-scoped** — every endpoint
here only ever touches `WHERE recipient_id = <you>`, for every role
including admin. A notification that isn't yours returns `404`, not
`403` — this is a deliberate IDOR/enumeration defense: the failure for
"not yours" and "doesn't exist" look identical, so no endpoint here ever
confirms another user's notification even exists.

`related_resource_id` is **not** a database foreign key — it's a
polymorphic pointer (`related_resource_type` says which kind of thing:
`home_visit`, `assistance_request`, `inventory_item`, `volunteer_profile`,
...). A single SQL FK can only target one table; the alternative (one
nullable FK column per possible target) is worse bloat for a field whose
only job is "let the user navigate to what this is about." If the target
is later deleted the notification becomes a dead link — a minor UX gap,
not a data-integrity problem like every other FK in this system.

## What triggers a notification today

Event-driven only — this codebase has no scheduler/cron, so time-based
reminders (medication, home-visit, upcoming-activity) are **not** wired
automatically in this phase, even though `notification_type` includes
them (for manual/future use). Wired triggers:

| Event | Recipient | Type |
|---|---|---|
| Home visit assigned (on create or reassignment via PATCH) | the assignee | `Home Visit Assignment` |
| Assistance request assigned (on create or reassignment via PATCH) | the assignee | `Assistance Request Assignment` |
| Stock movement crosses at/below minimum stock (not on every subsequent movement while already low — only the transition) | every `admin`/`staff` | `Low Inventory Alert` |
| A volunteer's profile status is set to `Verified` | that volunteer | `Volunteer Verified` |

Not wired (no unambiguous single recipient exists for these in the
current data model — no caregiver-to-elderly-member assignment exists to
notify): `Health Follow-up`, `Incident Follow-up`.

Notification object:
```json
{
  "id": 1, "notification_type": "Home Visit Assignment",
  "title": "Home visit assigned to you",
  "message": "You have been assigned a home visit for Mary Achieng.",
  "related_resource_type": "home_visit", "related_resource_id": 4,
  "is_read": false, "read_at": null, "created_at": "..."
}
```

## GET /api/notifications

- **Auth:** any valid token — always scoped to the caller.
- **Query params (optional):** `unread_only` (`true`), `notification_type`, `page` (default 1), `per_page` (default 20, max 100).
- **Response `200`:** `{ "notifications": [...], "pagination": { "page", "per_page", "total", "pages" } }`, newest first.

## GET /api/notifications/unread-count
- **Auth:** any valid token. Response `200`: `{ "unread_count": 3 }`.

## PATCH /api/notifications/{id}
- **Auth:** must be the recipient.
- **Request:** `{ "is_read": true | false }` — the only mutable field; there's no way to edit a notification's content, only its read state. Setting `is_read: true` stamps `read_at`; setting it back to `false` clears `read_at`.
- **Response `200`:** `{ "notification": { ... } }`. **Errors:** `404` if it isn't yours or doesn't exist (deliberately indistinguishable — see above); `400` if `is_read` is missing/invalid.

## POST /api/notifications/mark-all-read
- **Auth:** any valid token. Marks every unread notification belonging to the caller as read in one query. Response `200`: `{ "updated": 3 }` (count actually changed).

## DELETE /api/notifications/{id}
- **Auth:** must be the recipient. Response `204`. Errors: `404` if it isn't yours or doesn't exist.
