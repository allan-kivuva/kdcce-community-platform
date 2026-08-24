# KDCCE Community Platform

Software for Kibera Day Care Centre for the Elderly (KDCCE): a public site
(programs, gallery, blog, donations, craft shop) today, growing into an
internal elderly-care operations system (elderly member records, attendance,
health & wellness, home visits, volunteer management, and more).

This is a group project. The repo is split so frontend and backend teams can
work independently against a documented API contract.

```
kdcce-community-platform/
├── frontend/     React + Vite + Tailwind. See frontend/README.md.
├── backend/      Flask API + SQLAlchemy + JWT auth. See backend/README.md.
├── docs/api/     API contract: one file per module, endpoint/method/auth/
│                 request/response/errors/role. Read before wiring a new
│                 frontend screen to an existing or new endpoint.
└── docker-compose.yml   Dev environment: both services with hot reload.
```

## Quickstart

### Option A — Docker (both services at once)

```bash
docker compose up
```

Frontend: `http://localhost:5173`. Backend: `http://localhost:5000`.

First run only, apply migrations inside the backend container:

```bash
docker compose exec backend flask db upgrade
```

### Option B — Run each side natively

See `backend/README.md` and `frontend/README.md` for full setup. Short version:

```bash
# backend
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env
FLASK_APP=wsgi.py ./.venv/bin/python3 -m flask db upgrade
./.venv/bin/python3 -m flask run --port 5000

# frontend (separate terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Demo Login Credentials

⚠️ **These credentials are for local development/demo purposes only. Do
not use them in production, and never seed a real deployment with a
password this simple.**

A fresh clone has an empty database — none of these accounts exist until
someone creates them locally by running the seed commands below. They're
not hardcoded into the app; they're just what running those commands with
these specific values produces.

### Admin

```
Email:    admin@kdcce.local
Password: changeme123
```

### Volunteer 1 (Verified — assigned Elderly 1–4)

```
Email:    grace.mwangi@example.com
Password: GraceDemo2026!
```

### Volunteer 2 (Verified — assigned Elderly 5–8)

```
Email:    daniel.otieno@example.com
Password: DanielDemo2026!
```

### Volunteer 3 (Verified — assigned Elderly 9–12)

```
Email:    faith.wanjiru@example.com
Password: FaithDemo2026!
```

### Volunteer 4 (Verified — assigned Elderly 13–16)

```
Email:    samuel.kiptoo@example.com
Password: SamuelDemo2026!
```

### Volunteer 5 (Verified — assigned Elderly 17–20)

```
Email:    esther.njeri@example.com
Password: EstherDemo2026!
```

### Demo data

Running `flask seed-demo` (see below) creates:

- **5 volunteers**, all `Verified` — different skills, availability,
  experience and areas of interest each, so the admin volunteer list
  looks realistic rather than identical rows.
- **20 elderly members** — fictional Kibera-area residents with varied
  gender, age, OPA/community-group membership (2 demo OPAs, some members
  in neither), emergency contacts, health notes, allergies, dietary
  requirements, and vulnerability notes.
- **20 home-visit assignments** — the existing `HomeVisit.assigned_to_id`
  mechanism, 4 elderly members assigned to each volunteer in order
  (Volunteer 1 → Elderly 1–4, Volunteer 2 → Elderly 5–8, ...), each
  firing the normal assignment notification.

All fictional, all `@example.com`, no real person's information.

### Running the demo seed

```bash
cd backend

# 1. Create the admin account (needed first — the demo seed needs an
#    existing admin/staff user to record as who requested each visit)
FLASK_APP=wsgi.py ./.venv/bin/python3 -m flask seed-admin \
  --name "Admin" --email "admin@kdcce.local" --password "changeme123" --role admin

# 2. Create the 5 volunteers, 20 elderly members, and their assignments
FLASK_APP=wsgi.py ./.venv/bin/python3 -m flask seed-demo
```

`seed-demo` is idempotent — every insert is guarded by an existence check
first (by email, elder name, or OPA name), so running it again after it's
already run fills in anything missing and never creates duplicates. It
never deletes, resets, or modifies existing data.

Want a volunteer application in a non-Verified state to test that flow
too (e.g. the "application under review" or "not approved" portal
screens)? That still has to go through the real public flow — register,
then have the admin approve/reject it via `/admin/volunteers` or:

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"...","email":"...@example.com","password":"..."}'
```

## Team ownership

- **Frontend team** works in `frontend/`: pages, components, forms, tables,
  dashboards, API integration (via `frontend/src/lib/api.js`), responsive
  design, accessibility.
- **Backend team** works in `backend/`: Flask blueprints, SQLAlchemy models,
  Alembic migrations, auth/RBAC, validation (Marshmallow schemas), business
  logic, pytest tests.
- **API contract** lives in `docs/api/` and is the shared source of truth
  between the two — update it in the same PR that adds or changes an
  endpoint, so the other side never has to guess the shape of a request or
  response.

## Branching

One feature branch per module, e.g. `feature/elderly-management`,
`feature/attendance`, `feature/home-visits`, `feature/volunteer-management`,
`feature/feeding`, `feature/health-wellness`. Each new backend module gets
its own Flask blueprint (`backend/app/<module>/`) and its own doc file under
`docs/api/`; each new frontend feature gets its own page/manager component
under `frontend/src/pages/` — this keeps different people's branches from
touching the same files.

## Tests

```bash
cd backend && ./.venv/bin/python3 -m pytest tests/ -v
cd frontend && npm run build   # no frontend test suite yet
```
