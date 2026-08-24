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
