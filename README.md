# Tasca

A voice agent that answers the phone for **Tasca Tagarela**, a fictional Lisbon restaurant. It takes table reservations, answers questions about hours and the menu, and hands off to a human when needed — in European Portuguese.

Built with ElevenLabs Agents, Twilio, FastAPI, Postgres and React.

> 🚧 Work in progress.

## Quickstart

Requires Docker, [uv](https://docs.astral.sh/uv/) and Node 24.

```bash
docker compose up --build
```

- Admin dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs

### Running services individually

```bash
docker compose up -d postgres

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload --app-dir src

cd frontend
nvm use
npm install
npm run dev
```
