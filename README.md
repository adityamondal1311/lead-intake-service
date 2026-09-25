# Stylework Lead Intake Service

Receives Meta Ads leads via webhook, stores them with an append-only audit trail, and displays them
in a React dashboard.

> **Work in progress.** Full architecture, setup, deployment, trade-offs and scaling documentation
> will be added as the build progresses. Design decisions and AI usage are recorded in
> [AGENT.md](AGENT.md).

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 (uv for packaging) |
| Database | PostgreSQL, SQLAlchemy 2.x, Alembic *(upcoming)* |
| Frontend | React + TypeScript (Vite) |
| Deployment | Docker, Railway *(upcoming)* |
| CI | GitHub Actions: ruff + pytest (backend), oxlint + type-check + build (frontend) |

## Repository layout

```
backend/    FastAPI service (app factory, settings, health endpoint)
frontend/   React + TypeScript dashboard (Vite)
.github/    CI workflow
AGENT.md    AI usage, architecture decisions, contribution log
```

## Local development (current state)

### Backend

Requires [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 automatically.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload     # http://localhost:8000/health, /docs
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

### Frontend

Requires Node.js 20.19+ (CI uses Node 24).

```bash
cd frontend
npm install
npm run dev                               # http://localhost:5173
npm run lint && npm run build
```

## Progress

- [x] Phase 0: requirements frozen, ambiguities resolved (see AGENT.md)
- [x] Phase 1: backend and frontend skeletons, CI
- [ ] Phase 2: PostgreSQL, SQLAlchemy, Alembic, DB-aware health check
  - [x] Database infrastructure: Postgres via Docker Compose, settings, engine/session, Alembic
  - [x] DB-aware `/health` (503 when Postgres is unreachable), JSON logging, request IDs
  - [ ] Tests against real Postgres, CI Postgres service
- [ ] Phase 3+: data model, lead APIs, webhook, frontend, tests, Docker, deployment
