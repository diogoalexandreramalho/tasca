# Tasca

Phone voice agent for a fictional Lisbon restaurant (Tasca Tagarela): reservations, FAQs, human handoff. Agent speaks European Portuguese; code, docs and commits are in English.

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
```

Backend imports are absolute from `src/`: `from core.config import ...` — `src/` is on `sys.path` via pytest `pythonpath`, alembic `prepend_sys_path` and uvicorn `--app-dir`.

## Commands

```bash
# Backend
cd backend && uv sync
uv run uvicorn main:app --reload --app-dir src
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run alembic upgrade head
```

## Conventions

- **Errors**: raise `AppException` subclasses from `core/exceptions.py`. Don't return ad-hoc error JSON.
- **Layering**: endpoint → service → repository → model. Services commit; repositories don't.
- **Time**: store `timestamptz` in UTC; business rules (sittings, opening days) are in `Europe/Lisbon`.

## Git workflow

- Short-lived branches off `main`, named `<type>/<slug>` (e.g. `feat/booking-core`).
- Commits: `<type>(<scope>): <imperative summary>`. Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`. Scopes: `api`, `db`, `agent`, `sms`, `frontend`, `tests`, `ci`, `deps`.
- No direct pushes to `main`; open a PR and squash-merge. PR body: Summary / Test plan / Notes.

Update this file when a non-obvious convention or gotcha is introduced.
