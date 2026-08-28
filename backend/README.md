# KDCCE API (backend)

Flask backend for the KDCCE course project. Step 1 of the plan in
`.claude/plans/calm-meandering-dragon.md`: app skeleton, database,
migrations, and JWT auth (register/login/refresh/me) with three roles
(`admin`, `staff`, `volunteer`). Everything else in that plan — donations,
content CRUD, messaging, tasks, hours, events, announcements, notifications —
is not built yet.

## Setup

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt   # if pip is missing, see below
cp .env.example .env
export FLASK_APP=wsgi.py
./.venv/bin/python3 -m flask db upgrade        # creates instance/kdcce.db
./.venv/bin/python3 -m flask run --port 5000
```

If `python3 -m venv` gives you an environment with no `pip` (some minimal
Linux images ship Python without `ensurepip`), bootstrap it manually instead
of `apt install`ing anything:

```bash
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
python3 -m venv .venv --without-pip
./.venv/bin/python3 /tmp/get-pip.py
./.venv/bin/python3 -m pip install -r requirements.txt
```

The API listens on `http://localhost:5000`. CORS is scoped to
`http://localhost:5173` (the Vite dev server) via `CORS_ORIGINS` in `.env`.

## Tests

```bash
./.venv/bin/python3 -m pytest tests/ -v
```

## Endpoints (so far)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/health` | none | liveness check |
| POST | `/api/auth/register` | none | always creates a `volunteer` — role is never taken from the client |
| POST | `/api/auth/login` | none | returns access + refresh JWTs |
| POST | `/api/auth/refresh` | refresh token | returns a new access token |
| GET | `/api/auth/me` | access token | returns the authenticated user |

`/api/auth/register` and `/api/auth/login` are rate-limited (10/min per IP).

## Database

SQLite at `backend/instance/kdcce.db` by default (created by `flask db
upgrade`). Set `DATABASE_URL` in `.env` to a Postgres URL to point at a real
database instead — no code changes needed, SQLAlchemy handles the dialect
difference. Every schema change goes through `flask db migrate` /
`flask db upgrade`, never a hand edit.

## Connecting the frontend

Nothing in `../src` calls this API yet — the frontend still only has its
local mock/`localStorage` state. Wiring `AdminLogin.jsx` to
`POST /api/auth/login` is the natural next step once this piece is reviewed.
