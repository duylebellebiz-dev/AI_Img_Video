# NailSocial AI — Phase 1

Batch Image Generator + Prompt Intelligence + Image Quality Agent. See
[CLAUDE.md](CLAUDE.md) for full scope; publishing/captions/hashtags/billing
are intentionally out of scope for this phase.

## Stack

- Backend: FastAPI + SQLAlchemy, Python 3.11 (batch/edit jobs run via FastAPI `BackgroundTasks`, no separate worker process)
- DB: PostgreSQL (already running locally as a Windows service)
- Storage: local disk by default; Cloudflare R2 (S3-compatible) as the durable copy when `R2_*` env vars are set — needed on hosts without a persistent disk
- Frontend: React + Vite + Tailwind v4

## One-time setup

### 1. Create the Postgres database

Run via `psql` (as the postgres superuser) or pgAdmin:

```sql
CREATE USER nailsocial WITH PASSWORD 'change-me-locally';
CREATE DATABASE nailsocial OWNER nailsocial;
GRANT ALL PRIVILEGES ON DATABASE nailsocial TO nailsocial;
```

Use a real password instead of `change-me-locally` if this machine isn't
purely local dev.

### 2. Backend

```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt
cp .env.example .env   # then fill in DATABASE_URL password to match step 1
```

Leave `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` blank to run in **mock mode**
(deterministic placeholder prompts/images) — the full pipeline works end to
end without real API access. Fill them in later to switch to real calls.

### 3. Frontend

```bash
cd frontend
npm install
```

## Running everything (2 processes, in separate terminals)

```bash
# 1. API server (batch/edit jobs run in-process via FastAPI BackgroundTasks)
cd backend && ./.venv/Scripts/uvicorn app.main:app --reload --port 8000

# 2. Frontend dev server
cd frontend && npm run dev
```

Then open http://localhost:5173. Uploads/status calls are proxied to the API
at `127.0.0.1:8000` (see `frontend/vite.config.js`).

## How `num_images` behaves in each pairing mode

`num_images` (1-100) is always authoritative — whatever the pairing mode
produces as its "natural" set of combinations, the system loops through that
set and repeats pairs (with an incrementing `variation` number, which feeds
into prompt/image variation) until exactly `num_images` images have been
generated. It never silently caps at the number of natural combinations, and
it never drops images to fit — see [`pairing_service.py`](backend/app/services/pairing_service.py).

- **Cross Pair**: base set = every design x every pose. E.g. 3 designs x 2
  poses = 6 base pairs. If `num_images=20`, those 6 pairs are cycled through
  until 20 images exist (pairs repeat: 6, 6, 6, then 2 more).
- **Random Pair**: base set size = `max(len(designs), len(poses))`, each
  slot randomly assigned a design + a pose. Same cycling behavior applies
  above that base size.
- **One-to-One**: designs and poses are paired by index; if the lists are
  different lengths, the shorter one cycles to match the longer one. Same
  cycling behavior applies above that base size.

If every attempted image fails the Image Quality Agent's threshold after
retries, it's kept and marked `needs_review` rather than dropped — so the
final delivered count (rows in the DB, images in the ZIP) still matches
`num_images`, even if some entries need a human look.

## Module map

| Module | Code |
|---|---|
| 1. Batch Image Generator | `backend/app/routers/batch.py`, `backend/app/tasks/batch_tasks.py`, `backend/app/services/pairing_service.py` |
| 2. Prompt Intelligence | `backend/app/services/agent_service.py` |
| 3. Image Quality Agent | `backend/app/services/quality_service.py` |
| Image generation/editing | `backend/app/services/image_service.py` |
| Storage (originals/generated/ZIP) | `backend/app/services/storage_service.py` |
| Publishing (stub only, Phase 4) | `backend/app/services/publishing_service.py` |

## Tests

```bash
cd backend && ./.venv/Scripts/pytest tests/ -v
```
