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
   push to GitHub."* → this commit set.

## Verification Process

- Every phase ends with `ruff check`, `ruff format --check` and `pytest` (backend), and
  `npm run lint` (oxlint) and `npm run build` (`tsc -b` + Vite) (frontend). CI repeats these on every push.
- I read generated code before committing. Anything I can't explain gets simplified or rewritten.
- Backend behaviour that depends on the database (constraints, locking, idempotency) will be tested
  against real PostgreSQL, not SQLite.

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
