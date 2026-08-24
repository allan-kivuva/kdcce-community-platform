# Follow-ups

`backend/app/followups/` — turns the `follow_up_required` flag already on
`HealthRecord`, `HomeVisit`, `AssistanceRequest`, and `Incident` into an
actual, assignable, trackable task. Those 4 models already had the flag;
nothing acted on it before this module existed.

**Auto-creation, not a form to fill in separately**: when staff set
`follow_up_required: true` on any of those 4 records — at creation, or on
a `False → True` transition via `PATCH` — a `FollowUp` is created
automatically (see the hooks in `health/routes.py`, `homevisits/routes.py`,
`assistance/routes.py`, `incidents/routes.py`, all calling the same
`followups/service.py:create_from_source()` chokepoint). Re-saving an
already-`True` flag does not create a second one. A `FollowUp` can also be
created directly (`source_type: "manual"`) for something with no natural
source record, e.g. a phone call from a family member.

`source_type`/`source_id` is a polymorphic pointer (not a database FK) —
same tradeoff as `Notification.related_resource_id` and
`AssignmentMessage`: a single FK can't target 4 different tables.
`elderly_member_id` **is** a real FK, unlike the source pointer — every
follow-up is about one specific person, and that's what every list/filter
actually queries by.

`is_overdue` is **computed**, never stored: `status != "Completed" and
due_date < today`. Same reasoning as this app's other derived views (e.g.
low-stock is a live column comparison, not a stored flag).

Follow-up object:
```json
{
  "id": 1, "elderly_member_id": 3, "elderly_member_name": "Alice Wambui", "elderly_member_code": "KDCCE-2026-0003",
  "source_type": "health_record", "source_id": 7, "reason": "Arrange a physiotherapy check-in.",
  "priority": "Medium", "assigned_to_id": 5, "assigned_to": "Grace Mwangi",
  "due_date": null, "status": "Pending", "is_overdue": false, "notes": null,
  "completed_at": null, "created_by": "Admin", "created_at": "...", "updated_at": "..."
}
```

## Authorization

Same pattern as `HomeVisit`/`AssistanceRequest`: `admin`/`staff` see and
manage everything; a `volunteer` only ever sees follow-ups
`assigned_to_id` them, and only while their `VolunteerProfile.status` is
currently `Verified` (re-checked on every request — a follow-up assigned
to a volunteer who's later rejected stops being visible to them, same as
their visits/requests do).

## POST /api/followups
- **Auth:** `admin`, `staff`.
- **Request:** `{ "elderly_member_id", "reason", "priority" (optional, default Medium), "assigned_to_id" (optional — must be staff/admin or a Verified volunteer), "due_date" (optional, YYYY-MM-DD), "notes" (optional) }`.
- **Response `201`:** `{ "followup": { ... } }`, `source_type: "manual"`.

## GET /api/followups
- **Auth:** any valid token — scoped as described above.
- **Query params (optional, admin/staff only for `elderly_member_id`/`assigned_to_id`):** `status`, `priority`, `elderly_member_id`, `assigned_to_id`, `overdue` (`true`), `page`, `per_page` (max 200).
- **Response `200`:** `{ "followups": [...], "pagination": { ... } }`.

## GET /api/followups/{id}
- **Auth:** as above. Errors: `403`, `404`.

## PATCH /api/followups/{id}
- **`admin`/`staff`:** any subset of `priority`, `assigned_to_id`, `due_date`, `status`, `notes`. Reassigning notifies the new assignee (`Follow-up Assigned`, via the existing `notify()`).
- **The assigned user, on their own follow-up:** only `status` (`In Progress` or `Completed`) and `notes` — not priority, due date, or reassignment. Setting `status: "Completed"` stamps `completed_at` the first time.
- **Errors:** `400`, `403`, `404`.
