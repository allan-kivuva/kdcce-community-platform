# Assignment photo + private conversation + admin review

`backend/app/assignments/` — shared mechanics (file validation/storage,
message CRUD, review CRUD) behind the photo/message/review endpoints
documented per-module in
[home-visits.md](home-visits.md#photo-and-private-conversation) and
[assistance.md](assistance.md#photo-and-private-conversation). No new
blueprint and no new page — the routes live directly in `homevisits/routes.py`
and `assistance/routes.py`, matching this codebase's established pattern of
each module owning its own routes rather than a shared generic blueprint.

## Why not the existing (Phase 7D) Inbox?

`InboxMessage` is a shared, ownerless mailbox for anonymous public
contact-form submissions — no sender, no thread, no link to any resource.
This feature is the opposite: a private, per-assignment, two-way thread
between exactly one volunteer and admin/staff. Reusing `InboxMessage`
would mean bolting an unrelated shape onto a table already doing its own
job. `AssignmentMessage` is a new, small model instead.

## Models

`AssignmentAttachment`, `AssignmentMessage`, and `AssignmentReview` (in
the central `models.py`, same as every other model in this app) all use
`assignment_type` (`"home_visit" | "assistance_request"`) + `assignment_id`
as a polymorphic pointer — **not** a database foreign key, deliberately,
the same tradeoff already made for `Notification.related_resource_id`: a
single FK can't target two tables, and a nullable FK column per possible
target is worse bloat for a field whose only job is "which assignment
does this belong to." At most one row per assignment for both
`AssignmentAttachment` ("a photo," not "photos") and `AssignmentReview`
("a review," not a review history) — submitting again replaces the
previous one.

`AssignmentReview` is deliberately **admin-only** to create
(`roles_required("admin")`, not the `("admin", "staff")` pair used
everywhere else in this app) and only accepted once the assignment's own
`status` is `Completed` (`409` otherwise) — rating unfinished work doesn't
make sense, and this is specifically an admin sign-off on completed work,
not a general staff capability.

## File storage

No file-upload mechanism existed anywhere in this app before this feature
(gallery/blog only ever stored image *URLs*). Photos are saved to disk
under `backend/instance/uploads/assignment_photos/<uuid4>.<ext>` —
`instance/` is never served by Flask's static route, so even someone who
knew the exact server path couldn't reach the file by URL; the only way to
read it is the authenticated `GET .../photo` endpoint. The filename is
always server-generated (`uuid4`); the client's original filename is kept
only as display metadata and is never used to build a filesystem path,
which makes path traversal structurally impossible rather than merely
filtered. The `mime_type` stored and served is what the server verified
from the file's own bytes (magic-byte signatures for JPEG/PNG/WebP), never
the client-supplied filename extension or `Content-Type` header — both are
attacker-controlled. Max 5MB, enforced twice: the application checks it
explicitly (`assignments/service.py`'s `MAX_PHOTO_SIZE`), and
`app.config["MAX_CONTENT_LENGTH"]` is a slightly higher hard backstop
enforced by Werkzeug before the request body is even parsed.

## Authorization

No new authorization concept for photo/messages. Every one of those
routes reuses the exact branch each module's own `GET`/`PATCH` already
applies to that resource (`_can_access_visit` / `_can_access_request`,
each a thin wrapper around the module's existing `_is_verified_volunteer`
check): `admin`/`staff` unconditionally; the assigned user only while
their `VolunteerProfile` status is currently `Verified` (so a volunteer
verified-then-later-rejected loses photo/message access to old
assignments the same way they already lose visit access — see the
portal-access-gate note in
[volunteers.md](volunteers.md#portal-access-gate)); everyone else gets
`403`, unauthenticated gets `401`. **Review is the one exception**:
`GET` uses the same `_can_access_*` rule, but `POST` is `admin`-only —
not staff, and not the assigned volunteer reviewing their own work.

## Notifications

Sending a message notifies the other party via the existing `notify()`
chokepoint (`notifications/service.py`) — no second notification system.
A volunteer's message notifies whoever requested the visit/request; a
staff/admin message notifies the assigned volunteer. Submitting a review
notifies the assigned volunteer/staff (`Assignment Reviewed`), the same
way.
