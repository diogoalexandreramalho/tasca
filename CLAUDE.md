# Tasca

Phone voice agent for a fictional Lisbon restaurant (Tasca Tagarela), plus an admin dashboard. The agent handles bookings only (check, book, find, cancel) and must never invent facts; it speaks European Portuguese. Code, docs and commits are in English. Deployed: Netlify (dashboard) → Render (API) → Neon (Postgres), configured in each provider's dashboard.

## Stack

- **Voice**: ElevenLabs Agents (STT/LLM/TTS) with native Twilio integration. ElevenLabs calls our backend as webhook tools.
- **SMS**: Twilio (alphanumeric sender ID).
- **Backend**: FastAPI, async SQLAlchemy 2, Alembic, Postgres 16. `uv`, `ruff`, `mypy --strict`.
- **Frontend** (admin dashboard): React + TS + Vite, TanStack Query, Tailwind.

## Layout

```
backend/src/
  main.py              # app factory
  api/v1/              # router.py, endpoints/
  core/                # config, exceptions, logging
  db/                  # base (DeclarativeBase + TimestampMixin), session
  models/ schemas/ services/ repositories/
backend/alembic/       # migrations
frontend/src/
  app/                 # App, providers, routes
  features/<name>/     # pages, hooks, types per feature
  lib/                 # api.ts (request wrapper, ApiError), queryClient
```

Backend imports are absolute from `src/`: `from core.config import ...` — `src/` is on `sys.path` via pytest `pythonpath`, alembic `prepend_sys_path` and uvicorn `--app-dir`.

## Commands

```bash
# Postgres only (host port 5432 — stop Artlas's DB first if it's running)
docker compose up -d postgres

# Backend
cd backend && uv sync
uv run alembic upgrade head
PYTHONPATH=src uv run python -m db.seed        # tables + sittings (idempotent)
uv run uvicorn main:app --reload --app-dir src
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests

# Frontend (Node 24 — `nvm use`)
cd frontend && npm install
npm run dev
npm run typecheck
npm test

# Full stack
docker compose up --build
```

Health check: `GET /api/v1/health`.

## Conventions

- **Errors**: raise `AppException` subclasses from `core/exceptions.py`. Don't return ad-hoc error JSON. FastAPI's own validation 422s are converted to `ValidationAppError`, so every error is `{code, message, details}`.
- **Auth**: one admin account from env (`ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, `JWT_SECRET_KEY`), no users table. `POST /api/v1/auth/token` (OAuth2 password form) → 12 h bearer token. Routers are protected in `api/v1/router.py` with `dependencies=[Depends(require_admin)]`; only `/health` and `/auth/token` are public. Generate the hash with `PYTHONPATH=src uv run python -m core.hash_password` and keep it single-quoted in `.env` (it contains `$`). The app won't start without these vars.
- **Layering**: endpoint → service → repository → model. Services commit; repositories don't.
- **Agent tools** (`api/v1/endpoints/agent.py`, schemas in `schemas/agent.py`): protected by the `X-Agent-Secret` header (`AGENT_API_SECRET`, optional; unset = every `/agent` route is 401). Reuse the dashboard's services; reply with only the facts the model needs next (no wording, no other customers' data, no table numbers). Business outcomes are HTTP 200: read tools return an empty list (+ `reason`/`field`), write tools a `status`. Inputs the model may get wrong (time, ids) are strings so they come back as `invalid`/`not_found`, not 422. Find and cancel require the booking's phone; cancel answers `not_found` for someone else's booking.
- **Time**: store `timestamptz` in UTC; business rules (sittings, opening days) are in `Europe/Lisbon`.
- **Booking rules** live in `services/booking_rules.py` as pure functions (`now` is passed in, never read from the clock) so they're unit-testable. Party-size-vs-table-capacity is enforced only there, not in the DB (a CHECK can't read another table).
- **Frontend API**: always `request()` from `lib/api.ts`, never raw `fetch`. Query keys: `['resource', ...inputs]`.
- **Pre-commit**: `pre-commit install` once per clone. Keep the ruff hook `rev` in sync with ruff in `backend/uv.lock`. CI (`.github/workflows/ci.yml`) runs the full backend + frontend checks.

## Git workflow

- Short-lived branches off `main`, named `<type>/<slug>` (e.g. `feat/booking-core`).
- Commits: `<type>(<scope>): <imperative summary>`. Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`. Scopes: `api`, `db`, `agent`, `sms`, `frontend`, `tests`, `ci`, `deps`.
- No direct pushes to `main`; open a PR and squash-merge. PR body: Summary / Test plan / Notes.

## Tests

- `tests/unit/`: pure functions, no DB. Run by the pre-commit hook.
- `tests/integration/`: real Postgres in a separate `tasca_test` DB (created + migrated from scratch per run; override with `TEST_DATABASE_URL`). Needs `docker compose up -d postgres`. Never touches the dev `tasca` DB.
- Services take `now` as a parameter — pass a fixed datetime in tests, never rely on the real clock.
- Race tests use the `force_collision` fixture (a barrier) so both bookings really read before either inserts. Without it the second call is still connecting when the first commits and the retry path never runs.

Update this file when a non-obvious convention or gotcha is introduced.
