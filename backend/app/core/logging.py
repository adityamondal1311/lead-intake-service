import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Set by the request middleware; every log line written while handling a request carries it,
# so all logs for one request can be found with a single filter.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has. Anything else on a record came from `extra={...}`.
# color_message is uvicorn's ANSI-coloured duplicate of the message; useless in JSON.
_RESERVED = set(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "taskName",
    "color_message",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line on stdout: easy to search in Railway or any log pipeline."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            entry["request_id"] = request_id
        entry.update({k: v for k, v in vars(record).items() if k not in _RESERVED})
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Route uvicorn's own logs through the JSON handler. Its access log is turned off because the
    # request middleware writes a richer access line (request id, duration).
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False
