import json
import logging

from app.core.logging import JsonFormatter, request_id_var


def _format(record: logging.LogRecord) -> dict[str, object]:
    return json.loads(JsonFormatter().format(record))


def test_json_log_line_includes_extras_and_current_request_id() -> None:
    record = logging.makeLogRecord(
        {"name": "app.request", "levelname": "INFO", "msg": "request completed", "status_code": 200}
    )
    token = request_id_var.set("req-1")
    try:
        entry = _format(record)
    finally:
        request_id_var.reset(token)

    assert entry["message"] == "request completed"
    assert entry["request_id"] == "req-1"
    assert entry["status_code"] == 200
    assert "timestamp" in entry


def test_json_log_line_omits_request_id_outside_a_request() -> None:
    entry = _format(logging.makeLogRecord({"msg": "startup"}))

    assert "request_id" not in entry
