#!/bin/sh
# Container entrypoint.
#
#   docker run <image>                 → (migrations) then the API server
#   docker run <image> <command...>    → (migrations) then <command> instead of the server,
#                                        e.g. `alembic upgrade head` as a release step
#
# RUN_MIGRATIONS_ON_START (default true) decides whether migrations run here:
#   true  — local Docker / compose: one instance, so migrating at start is simplest.
#   false — Railway: migrations run once per deploy as the pre-deploy (release) step instead,
#           so application replicas never race to migrate.
#
# `set -e`: a failed migration exits non-zero, so the API never starts against a schema it does
# not expect (and on Railway a failed pre-deploy stops the deploy).
set -eu

log() {
  echo "{\"level\": \"INFO\", \"logger\": \"entrypoint\", \"message\": \"$1\"}"
}

case "${RUN_MIGRATIONS_ON_START:-true}" in
  true)
    log "applying database migrations"
    alembic upgrade head
    ;;
  false)
    log "skipping migrations at start (RUN_MIGRATIONS_ON_START=false)"
    ;;
  *)
    # Same rule as the app's settings: an unrecognised value is an error, not a guess.
    echo "RUN_MIGRATIONS_ON_START must be true or false" >&2
    exit 1
    ;;
esac

# A command was given: run it in place of the server.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# `exec` replaces this shell with uvicorn, so uvicorn is PID 1 and receives the container's
# SIGTERM directly: a graceful shutdown instead of being killed when the stop timeout expires.
# PORT is set by Railway; 8000 locally. --proxy-headers trusts X-Forwarded-For/-Proto from the
# platform's proxy (the real client address and https scheme).
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
