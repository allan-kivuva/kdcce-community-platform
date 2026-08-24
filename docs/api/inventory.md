# Inventory

`backend/app/inventory/` — food/resource stock tracking. All endpoints
require `admin` or `staff`.

**`current_stock` is never a request field, on create or edit** — it is
a running total maintained *only* by posting a `StockMovement` (see
below), inside one DB transaction alongside the movement row itself. This
is the core invariant of the module: the balance is always derivable from,
and kept in sync with, the movement ledger — never a separately-editable
number that could drift from it. Sending `current_stock` in any request
body is rejected as an unknown field (`400`), not silently ignored.

Inventory item object:
```json
{
  "id": 1, "name": "Rice", "category": "Food", "unit": "kg",
  "current_stock": 40.0, "minimum_stock": 10.0, "low_stock": false,
  "notes": null, "created_at": "...", "updated_at": "..."
}
```
`low_stock` is computed (`current_stock <= minimum_stock`), not stored.
`category` is one of `Food | Medical | Hygiene | Equipment | Other`.

Stock movement object (append-only — **no edit or delete endpoint,
ever**; a mistaken entry is corrected with a compensating movement, not
by rewriting history):
```json
{
  "id": 1, "item_id": 1, "movement_type": "In", "quantity": 50.0,
  "reason": "Donation received", "expiry_date": "2026-12-31",
  "donation_id": 3, "recorded_by": "Jane Staffer", "created_at": "..."
}
```
`donation_id` is an optional link to a logged [donation](donations.md)
this stock-in came from — not every stock-in has one. `expiry_date` only
applies to `In` movements; if sent on an `Out` movement it's silently
dropped (an item being removed doesn't have a new expiry).

## POST /api/inventory

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "name": "string, required, max 150, must be unique",
    "category": "Food | Medical | Hygiene | Equipment | Other, optional, default Other",
    "unit": "string, required, max 30",
    "minimum_stock": "number >= 0, optional, default 0",
    "notes": "string, optional, max 2000"
  }
  ```
  `current_stock` always starts at `0` — to seed an initial quantity, follow up with a stock-in movement.
- **Response `201`:** `{ "item": { ... } }`
- **Errors:** `400` validation; `409` if the name already exists.

## GET /api/inventory

- **Auth:** `admin` or `staff`.
- **Query params (optional):** `category`, `low_stock` (`true` to return only items where `current_stock <= minimum_stock` — this is the low-stock alert list).
- **Response `200`:** `{ "items": [ { ... }, ... ] }`, alphabetical.

## GET /api/inventory/{id}
- **Auth:** `admin` or `staff`. Response `200`: `{ "item": { ... } }`. Errors: `404`.

## PATCH /api/inventory/{id}
- **Auth:** `admin` or `staff`. Partial subset of `name`, `category`, `unit`, `minimum_stock`, `notes` — **not** `current_stock`. Omitted fields are left unchanged. Response `200`: `{ "item": { ... } }`. Errors: `400`, `404`, `409` (renaming to an existing name).

## DELETE /api/inventory/{id}
- **Auth:** `admin` only. Response `204`. Errors: `404`; `409` if this item has any stock movement history — the ledger is permanent, so what it's attached to can't be deleted out from under it.

## POST /api/inventory/{id}/movements

Record a stock-in or stock-out. Updates `current_stock` atomically in the
same transaction as the movement row.

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "movement_type": "In | Out, required",
    "quantity": "number > 0, required",
    "reason": "string, optional, max 1000",
    "expiry_date": "YYYY-MM-DD, optional, In only",
    "donation_id": "integer, optional — must reference an existing donation"
  }
  ```
- **Response `201`:** `{ "movement": { ... }, "item": { ... } }` — the item's `current_stock` reflects the new balance.
- **Errors:** `400` validation; `400` if an `Out` movement's `quantity` exceeds the item's current `current_stock` ("insufficient stock") — the balance is left untouched, the movement is not created; `404` unknown item.

## GET /api/inventory/{id}/movements
- **Auth:** `admin` or `staff`. Response `200`: `{ "movements": [ { ... }, ... ] }`, newest first — this is the item's full audit history. Errors: `404`.
