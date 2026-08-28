# Incidents

`backend/app/incidents/` — safeguarding/injury/medical incident reports.
Depends on [elderly.md](elderly.md). Every endpoint requires `admin` or
`staff` — **no volunteer access at all**, matching the role breakdown in
the brief, where "create incident reports" is a listed Caregiver/Staff
capability, not a Volunteer one.

**There is no `DELETE` endpoint.** An incident report is treated as a
permanent record (real safeguarding practice: retain, don't erase) —
correct a mistake by editing `status`/`resolution_notes`, never by
removing the row. `DELETE /api/incidents/{id}` returns `405 Method Not
Allowed`, not `403` — the route simply doesn't exist, for any role.

Incident object:
```json
{
  "id": 1, "elderly_member_id": 1, "elderly_member_name": "Mary Achieng",
  "elderly_member_code": "KDCCE-2026-0001", "reported_by": "Jane Staffer",
  "incident_type": "Fall", "severity": "Medium", "occurred_at": "2026-08-24T14:30:00+00:00",
  "location": "Dining hall", "description": "Slipped in the dining hall",
  "immediate_action_taken": "Assisted to a chair, checked for injury",
  "emergency_contact_notified": true, "emergency_contact_notified_at": null,
  "follow_up_required": true, "follow_up_notes": "Doctor visit tomorrow",
  "status": "Open", "resolution_notes": null,
  "created_at": "...", "updated_at": "..."
}
```
`incident_type`: `Fall | Injury | Medical Concern | Accident | Safeguarding
Concern | Other`. `severity`: `Low | Medium | High | Critical`, defaults
to `Medium`. `status`: `Open | Under Review | Resolved | Closed`.

**`severity: "Critical"` notifies every `admin`/`staff`** (via the
existing `notify()` chokepoint — no second notification path) — on
creation, or on a `PATCH` that transitions severity *into* `Critical`.
Re-saving an already-`Critical` incident does not re-notify.

**`follow_up_required: true` auto-creates a [FollowUp](followups.md)** —
same transition-only rule (creation, or a `False → True` PATCH) as the
other 3 source modules.

## POST /api/incidents

- **Request:**
  ```json
  {
    "elderly_member_id": "integer, required",
    "incident_type": "required, see above",
    "severity": "Low | Medium | High | Critical, optional, default Medium",
    "occurred_at": "ISO datetime, optional — defaults to now",
    "location": "string, optional, max 150",
    "description": "string, required, max 4000",
    "immediate_action_taken": "string, optional, max 2000",
    "emergency_contact_notified": "boolean, optional, default false",
    "emergency_contact_notified_at": "ISO datetime, optional",
    "follow_up_required": "boolean, optional, default false",
    "follow_up_notes": "string, optional, max 2000"
  }
  ```
  `status` always starts `Open`; `resolution_notes` isn't accepted at creation.
- **Response `201`:** `{ "incident": { ... } }`
- **Errors:** `400` validation (unknown member, invalid type, missing description).

## GET /api/incidents

- **Query params (optional):** `elderly_member_id`, `incident_type`, `status`, `follow_up_required` (`true`/`false`).
- **Response `200`:** `{ "incidents": [ { ... }, ... ] }`, most recently occurred first.

## GET /api/incidents/{id}
- Response `200`: `{ "incident": { ... } }`. Errors: `404`.

## PATCH /api/incidents/{id}

- Partial subset of the create fields, plus `status` and `resolution_notes` — this is how an incident gets resolved (`{ "status": "Resolved", "resolution_notes": "..." }`).
- Omitted fields are left unchanged, never reset — in particular, omitting `emergency_contact_notified`, `follow_up_required`, `status`, or `occurred_at` never resets any of them to their creation-time defaults.
- **Errors:** `400`, `404`.
