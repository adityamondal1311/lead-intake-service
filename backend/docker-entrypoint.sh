#!/bin/sh
# Container entrypoint: apply migrations, then hand the process over to uvicorn.
#
# `set -e`: if the migration fails, the script (and so the container) exits non-zero and the API
# never starts against a schema it does not expect. Migrations are idempotent, so a restart just
# finds the database already at "head".
set -eu

echo '{"level": "INFO", "logger": "entrypoint", "message": "applying database migrations"}'
alembic upgrade head

# `exec` replaces this shell with uvicorn, so uvicorn is PID 1 and receives the container's
# SIGTERM directly: a graceful shutdown instead of being killed when the stop timeout expires.
# PORT is set by Railway; 8000 locally. --proxy-headers trusts X-Forwarded-For/-Proto from the
# platform's proxy (the real client address and https scheme).
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
