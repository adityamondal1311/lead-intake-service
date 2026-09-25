# AGENT.md

How AI tools were used to build this project, which decisions were made by a person, and how
AI output was verified. This file is kept up to date phase by phase, not reconstructed at the end.

## AI Tools Used

| Tool | Used for |
|---|---|
| ChatGPT | Early brainstorming of the architecture and working plan |
| Claude (chat) | Reviewing the plan, resolving spec ambiguities, choosing a deployment platform, phase-by-phase breakdown |
| Claude Code (VS Code extension) | Scaffolding, code generation, running lint/tests/builds, keeping docs updated |

## How AI Was Used

- **Planning:** turning the assignment PDF into a phased plan and listing the review questions
  each decision has to answer.
- **Scaffolding and boilerplate:** project skeletons, config, CI workflow.
- **Implementation:** code for each phase, generated against a written spec (tech stack, data model,
  API contracts, webhook algorithm) that was agreed on before any code was written.
- **Verification:** running ruff, pytest, ESLint and the TypeScript build after every phase.

I own every commit and push. AI suggests changes and commit messages.

## AI-Generated Sections

Updated per phase. The detail is in the [AI Contribution Log](#ai-contribution-log).

- Phase 0–1: `.gitignore`, README stub, this file's skeleton, backend skeleton (`app/main.py`,
  `app/core/config.py`, `app/api/routes/health.py`, test), Vite frontend cleanup, CI workflow.

## Human-Written / Human-Decided Sections

- Choice of stack (FastAPI over Node, PostgreSQL over MongoDB, Railway for deployment).
- Every interpretation of an ambiguous requirement in [Architecture Decisions](#architecture-decisions).
- Scope limits: no queue, no microservices, no auth for the admin API in this iteration.
- Commit granularity and the commit trail itself.

## Architecture Decisions

These resolve gaps in the assignment brief. Each one is a choice, written down so it can be
challenged, not treated as fixed.

### D1. Modular monolith

One FastAPI service with strict layering: **routes → services → repositories → SQLAlchemy**.
The domain is small (leads, activities, webhook deliveries). Microservices would add network hops,
deployment units and failure modes without solving a real problem here. Clear module boundaries
keep extraction possible later.

### D2. FastAPI + PostgreSQL

FastAPI gives Pydantic validation and OpenAPI docs for free, which suits an API-first service.
PostgreSQL gives the guarantees the design depends on: unique constraints, `ON CONFLICT`,
`SELECT ... FOR UPDATE`, JSONB and CHECK constraints.

### D3. Sync SQLAlchemy, not async

The workload is I/O-light CRUD. FastAPI runs sync endpoints in a threadpool. Sync sessions keep
transaction boundaries, row locking and tests simple. Async is a later option if profiling calls for it.

### D4. Lead statuses

`NEW`, `CONTACTED`, `QUALIFIED`, `CONVERTED`, `LOST`. New leads start as `NEW`. Any status can move
to any other status, because sales teams reopen lost leads. Setting the status a lead already has
is a **no-op**: 200, no write, no activity, so the audit trail stays free of noise. A strict
transition state machine is a future improvement.

### D5. What "Lead Updated" means

The brief lists a `LEAD_UPDATED` activity but no lead-edit endpoint. My reading: when a webhook
arrives with a **new `event_id`** for a lead that **already exists** (same Meta `lead_id`) and any
field differs, the lead is updated and a `LEAD_UPDATED` activity records a field-level diff. No
differences means no activity. A status change records only `STATUS_CHANGED`. This covers all three
activity types without inventing an endpoint the brief did not ask for.

### D6. Two separate deduplication keys

- Meta `lead_id` → `leads.external_id` (UNIQUE) → **lead identity**.
- `event_id` → `webhook_events(source, external_event_id)` (UNIQUE) → **delivery idempotency**.

A retry of the same delivery is ignored. A new delivery about the same lead can update it.

### D7. Webhook payload

A flat, normalized payload (`event_id`, `lead_id`, `full_name`, `email`, `phone`, campaign, form
and ad ids, `created_time`). A real Meta Lead Ads webhook sends only a `leadgen_id` and
page/form/ad ids, and the field data is then fetched from the Graph API. This service simulates the
**post-enrichment** payload. The Graph API fetch is out of scope.

### D8. Webhook authenticity

HMAC-SHA256 of the raw request body, keyed with `META_APP_SECRET`, compared in constant time
against the `X-Hub-Signature-256` header. This is Meta's real scheme. The `GET` verification
handshake (`hub.challenge`) is also implemented. The app refuses to start in production without
a secret.

### D9. Dashboard/API authentication

Out of scope for this iteration and documented as a known gap. The upgrade path is an API key or
SSO in front of the admin API.

### D10. Other defaults

UUID primary keys. All timestamps are UTC `timestamptz`. Phone numbers are stored as strings.
The raw webhook payload is stored only in `webhook_events`, and is never returned by the lead APIs
or logged. Deployment is on Railway (backend, frontend, managed Postgres). Decisions live here in
AGENT.md and are summarized in the README, with no separate DECISIONS.md.

### D11. Tooling

`uv` for Python packaging: fast, with a lockfile (`uv.lock`) for reproducible CI and Docker builds.
`ruff` for lint and formatting. CI runs from the first commit, so every later commit is proven to
lint, test and build.

## Important Prompts

Condensed, in order.

1. *"Read the assignment PDF and email, and build a complete working plan: architecture, data model,
   webhook reliability, testing, deployment, review questions."* → produced the working plan.
2. *"Review the plan and decide the ambiguous parts: statuses, what LEAD_UPDATED means, payload
   shape, deployment platform."* → decisions D4–D10. Railway was chosen for managed Postgres and
   Docker support with the least setup time.
3. *"Write a persistent project context file with the frozen decisions and a phase plan."* → the
   spec used to drive code generation phase by phase.
4. *"Complete phases 0 and 1: repo, docs seed, backend and frontend skeletons, CI. Commit as me and
   push to GitHub."* → the Phase 0–1 commit set.
5. *"Start Phase 2. Three commits: database infrastructure; health checks and request logging;
   tests, CI and docs."* → the Phase 2 commit set. Claude Code also installed Docker Desktop and
   enabled WSL2 on the dev machine (the reboot was done by me).
6. *"Start Phase 3. Two commits: models + migration once reviewed, applied and verified; then
   constraint tests + docs."* → the Phase 3 commit set.

## Verification Process

- Every phase ends with `ruff check`, `ruff format --check` and `pytest` (backend), and
  `npm run lint` (oxlint) and `npm run build` (`tsc -b` + Vite) (frontend). CI repeats these on every push.
- I read generated code before committing. Anything I can't explain gets simplified or rewritten.
- Backend behaviour that depends on the database (migrations, constraints, locking, idempotency) is tested
  against real PostgreSQL (Docker locally, a service container in CI), not SQLite.

## AI Contribution Log

### Phase 0: Requirements and decisions
- **AI generated:** first drafts of the decision write-ups, `.gitignore`, the README stub and this
  file's structure.
- **Human decided:** every decision in D1–D11, especially the LEAD_UPDATED interpretation, the
  two-key dedup model, and keeping auth and queues out of scope.
- **Verified by:** checking each decision against the assignment brief and the evaluation criteria.

### Phase 1: Skeleton
- **AI generated:** uv project and ruff/pytest config, `create_app()` factory, `Settings`
  (pydantic-settings), `/health` route and test, the cleaned-up Vite React-TS app, and the GitHub
  Actions workflow. Toolchain install (Git, Node LTS, uv) on the dev machine.
- **Human decided:** the app-factory pattern (lets tests build an app with test settings), no empty
  placeholder packages (each folder arrives with the commit that first gives it code), and CI set up
  from day one.
- **Caught and corrected during review:**
  - `uv init` defaulted to Python 3.14. It was pinned back to 3.12 (`requires-python = ">=3.12,<3.13"`,
    `.python-version`) to match the agreed stack, and the lockfile was regenerated.
  - The current Vite template ships `oxlint` instead of ESLint. It was kept, since it is fast and
    `npm run lint` behaves the same.
  - `strict: true` was made explicit in `tsconfig.app.json`.
  - CI uses Node 24, because Vite 8 needs Node ≥ 20.19.
- **Verified by:** `ruff check`, `ruff format --check` and `pytest` passing locally on Python 3.12.
  The frontend `lint` and `build` pass. Manual checks: `/health` returns `{"status":"ok"}`, `/docs`
  loads, and the Vite dev server serves the app.

### Phase 2: Database infrastructure
- **AI generated:** Docker Compose Postgres 17 service with a test-database init script, new settings
  (`DATABASE_URL`, `LOG_LEVEL`, Meta secrets), the `postgres://` → `postgresql+psycopg://` URL
  normalizer, SQLAlchemy engine/session factory, `get_db` dependency, declarative `Base` with a
  constraint naming convention, and Alembic config reading the URL from app settings.
- **Human decided:** split Phase 2 into three commits (infrastructure; health + observability;
  tests + CI + docs), Postgres 17, a separate `lead_intake_test` database so tests never touch dev data.
- **Verified by:** `ruff check`/`ruff format --check`, `pytest`, `alembic upgrade head --sql`
  (offline) and a manual check of URL normalization. The first commit was pushed before Docker was
  installed on the dev machine; the live check followed before the second commit: `docker compose up`
  → healthy Postgres, `lead_intake_test` created, `alembic upgrade head` connects to both databases.

### Phase 2: Health checks and request logging
- **AI generated:** `/health` running `SELECT 1` with a 503 response when the database is
  unreachable, a stdlib JSON log formatter, request-ID middleware (accepts a safe caller-supplied
  `X-Request-ID` or generates one, echoes it, logs method/path/status/duration only), and the
  health test adjusted to use a stub session until CI gets a Postgres service.
- **Human decided:** no JSON-logging dependency (a 30-line stdlib formatter is enough); never log
  bodies or query strings because they carry PII.
- **Caught and corrected during manual testing:** with Postgres stopped, `/health` hung for ~130 s
  before returning 503, because psycopg waits indefinitely to connect by default. Added
  `connect_timeout=5` to the engine; it now fails in ~5 s. Also dropped uvicorn's ANSI-coloured
  `color_message` field from JSON logs.
- **Verified by:** running uvicorn against Docker Postgres: 200 with DB up, 503 with DB stopped,
  200 again after restart; caller request id echoed, malformed request id replaced; ruff and pytest.

### Phase 2: Tests, CI and docs
- **AI generated:** test layout split into `tests/unit` (no database) and `tests/integration`
  (real Postgres); a root conftest that forces `DATABASE_URL` to `TEST_DATABASE_URL` before the app
  is imported; session-scoped Alembic `upgrade head` and per-test `TRUNCATE`; health tests for
  DB up, DB unreachable (a real refused connection, not a mock) and request-ID handling; unit tests
  for URL normalization and the JSON log formatter; a Postgres 17 service container in CI; README
  sections for local setup, environment variables, tests and observability.
- **Human decided:** schema for tests comes from the real migrations rather than `create_all()`,
  so every test run also proves the migrations; unit tests must stay runnable without Docker.
- **Caught and corrected during review:**
  - Alembic's `fileConfig` disables all existing loggers by default, which would have silenced the
    app's loggers whenever migrations run in-process (the test suite). Set
    `disable_existing_loggers=False`.
  - Ruff classified `alembic` as a first-party import because of the local `alembic/` folder, so
    import order differed between files. Declared it third-party in the ruff isort config.
- **Verified by:** 10 tests passing locally against Docker Postgres; ruff lint and format clean;
  CI green with the Postgres service.

### Phase 3: Models and first migration
- **AI generated:** `StrEnum`s for status / activity type / webhook outcome / source, with CHECK
  constraint SQL generated from them; typed `Mapped[]` models for `leads`, `activities` and
  `webhook_events`; the three list/timeline indexes; the autogenerated Alembic migration.
- **Human decided:** VARCHAR + CHECK over native Postgres ENUMs; `activities` deleted with their lead
  (CASCADE) but `webhook_events` kept with `lead_id` set NULL, so the record of a received delivery
  survives; no index on `webhook_events.lead_id` until a query needs one; no ORM relationships yet
  (repositories will query explicitly, avoiding hidden lazy loads).
- **Reviewed and corrected in the generated migration:** replaced legacy `typing.Union` annotations
  (and fixed `script.py.mako` so future migrations are generated lint-clean), removed the
  autogenerate boilerplate comments, renamed the truncated filename. Checked by hand: types,
  nullability, server defaults, constraint names, FK `ON DELETE` rules, `DESC` index ordering.
- **Verified by:** `alembic upgrade head` on the dev database and inspection with `psql \d`;
  `alembic check` reports no drift between models and migration; `downgrade base` → `upgrade head`
  round trip; a throwaway ORM script (rolled back) confirming defaults are populated after INSERT
  via `RETURNING`; ruff and the existing test suite.
