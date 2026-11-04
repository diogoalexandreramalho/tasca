# Tasca

A voice agent that answers the phone for **Tasca Tagarela**, a fictional Lisbon restaurant. It checks availability, books, finds and cancels table reservations over the phone, in English, and never invents facts. Staff manage bookings in an admin dashboard.

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
