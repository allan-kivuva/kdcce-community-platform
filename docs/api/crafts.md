# Crafts

`backend/app/crafts/` — public craft-shop listing + admin CRUD. No
checkout/payment flow — this is an inventory/status board (`Available` /
`Reserved` / `Sold`), not a store.

Craft object:
```json
{
  "id": 1, "title": "...", "category": "Beadwork", "maker": "...",
  "price": 1200.0, "status": "Available", "image": "/images/crafts.jpg",
  "description": "...", "created_at": "...", "updated_at": "..."
}
```

## GET /api/crafts

- **Auth:** none.
- **Response `200`:** `{ "crafts": [ { ... }, ... ] }`, newest first.

## POST /api/admin/crafts

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "title": "string, required, max 200",
    "category": "Beadwork | Knitting | Other, required",
    "maker": "string, required, max 120",
    "price": "number > 0, required",
    "status": "Available | Reserved | Sold, optional, default Available",
    "image": "string, optional, max 500",
    "description": "string, optional, max 2000"
  }
  ```
- **Response `201`:** `{ "craft": { ... } }`
- **Errors:** `400` validation.

## PATCH /api/admin/crafts/{id}

- **Auth:** `admin` or `staff`.
- **Request:** any subset of the create fields (partial).
- **Response `200`:** `{ "craft": { ... } }`
- **Errors:** `400` validation, `404`.

## DELETE /api/admin/crafts/{id}

- **Auth:** `admin` or `staff`.
- **Response `204`:** no body.
- **Errors:** `404`.
