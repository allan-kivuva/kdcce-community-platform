# Gallery

`backend/app/gallery/` — public image gallery + admin add/remove. No edit
endpoint — remove and re-add if the URL/caption changes.

Image object:
```json
{ "id": 1, "url": "/images/community.jpg", "caption": "...", "created_at": "...", "updated_at": "..." }
```

## GET /api/gallery

- **Auth:** none.
- **Response `200`:** `{ "images": [ { ... }, ... ] }`, newest first.

## POST /api/admin/gallery

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  { "url": "string, required, max 500", "caption": "string, optional, max 200" }
  ```
- **Response `201`:** `{ "image": { ... } }`
- **Errors:** `400` validation.

## DELETE /api/admin/gallery/{id}

- **Auth:** `admin` or `staff`.
- **Response `204`:** no body.
- **Errors:** `404`.
