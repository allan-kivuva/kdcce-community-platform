# Donations

`backend/app/donations/` — public donation form + admin/staff management.
No real payment gateway is integrated: `status` is an internal workflow
label (`Paid` default on create, editable to `Pending` by staff), never a
verified payment confirmation. `txn_id`/`receipt_id` are always server-generated.

Donation object:
```json
{
  "id": 1, "donor_name": "...", "donor_email": "...", "donor_phone": "...",
  "amount": 500.0, "currency": "KES", "frequency": "one-time",
  "campaign": null, "payment_method": "M-Pesa", "status": "Paid",
  "txn_id": "TXN-A1B2C3D4E5F6", "receipt_id": "KDCCE-2026-000001",
  "message": null, "created_at": "...", "updated_at": "..."
}
```

## POST /api/donations

- **Auth:** none (public donor form).
- **Request:**
  ```json
  {
    "donor_name": "string, required, max 120",
    "donor_email": "email, required",
    "donor_phone": "string, optional, max 40",
    "amount": "number > 0, required",
    "currency": "KES (only allowed value), optional, default KES",
    "frequency": "one-time | monthly, required",
    "campaign": "string, optional, max 120",
    "payment_method": "M-Pesa | Card (Stripe) | PayPal, optional",
    "message": "string, optional, max 2000"
  }
  ```
  `status`, `txn_id`, `receipt_id` are rejected/ignored if sent — never trust a client-supplied status.
- **Response `201`:** `{ "donation": { ... } }`
- **Errors:** `400` validation.

## GET /api/donations

- **Auth:** `admin` or `staff`.
- **Response `200`:** `{ "donations": [ { ... }, ... ] }`, newest first.

## GET /api/donations/export.csv

- **Auth:** `admin` or `staff`.
- **Response `200`:** `text/csv` file download (`Content-Disposition: attachment`). Columns: Donor, Email, Amount, Currency, Frequency, Campaign, Payment Method, Status, Transaction ID, Receipt ID, Date. Use `downloadFile()` from `frontend/src/lib/api.js`, not plain `fetch`.

## GET /api/donations/{id}

- **Auth:** `admin` or `staff`.
- **Response `200`:** `{ "donation": { ... } }`
- **Errors:** `404`.

## PATCH /api/donations/{id}

- **Auth:** `admin` or `staff`.
- **Request:** any subset of `donor_name`, `donor_email`, `donor_phone`, `amount`, `frequency`, `campaign`, `payment_method`, `status` (`Paid` | `Pending`). Partial — only send fields you're changing.
- **Response `200`:** `{ "donation": { ... } }`
- **Errors:** `400` validation, `404`.
