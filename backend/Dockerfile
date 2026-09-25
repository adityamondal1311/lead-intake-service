# syntax=docker/dockerfile:1

# Base images are pinned by version and digest so a rebuild months later uses the same bytes.
ARG PYTHON_IMAGE=python:3.12.14-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.18@sha256:3adc3706091ce7c2fe595e669628caedd6d951551b92b258b7e7dbe06d9440bc

FROM ${UV_IMAGE} AS uv

# ---- build: resolve nothing, install exactly what uv.lock says ---------------------------------
FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# Dependency files first: code changes do not invalidate this (slow) layer.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

# ---- runtime: Python + the virtualenv + the code; no uv, no dev tools, no tests ----------------
FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY alembic.ini docker-entrypoint.sh ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

USER app
EXPOSE 8000

# /health checks PostgreSQL too, so "healthy" means the API can actually serve requests.
# Standard library only: the slim image has no curl, and none is added just for this.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=4)"]

# Invoked through sh so it does not depend on the executable bit (not tracked on Windows).
ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
