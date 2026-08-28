# Blog

`backend/app/blog/` — public blog listing + admin CRUD. Public route only
ever returns `Published` posts; drafts are only visible to staff/admin via
the `/api/admin/blog` list.

Post object:
```json
{
  "id": 1, "title": "...", "excerpt": "...", "image": "/images/blog.jpg",
  "type": "Story", "status": "Published", "created_at": "...", "updated_at": "..."
}
```

## GET /api/blog

- **Auth:** none.
- **Response `200`:** `{ "posts": [ { ... }, ... ] }` — `status: "Published"` only, newest first.

## GET /api/admin/blog

- **Auth:** `admin` or `staff`.
- **Response `200`:** `{ "posts": [ { ... }, ... ] }` — all posts including drafts.

## POST /api/admin/blog

- **Auth:** `admin` or `staff`.
- **Request:**
  ```json
  {
    "title": "string, required, max 200",
    "excerpt": "string, optional, max 2000",
    "image": "string (URL/path), optional, max 500",
    "type": "Story | Skills | Update, optional, default Story",
    "status": "Published | Draft, optional, default Draft"
  }
  ```
- **Response `201`:** `{ "post": { ... } }`
- **Errors:** `400` validation.

## PATCH /api/admin/blog/{id}

- **Auth:** `admin` or `staff`.
- **Request:** any subset of the create fields (partial).
- **Response `200`:** `{ "post": { ... } }`
- **Errors:** `400` validation, `404`.

## DELETE /api/admin/blog/{id}

- **Auth:** `admin` or `staff`.
- **Response `204`:** no body.
- **Errors:** `404`.
