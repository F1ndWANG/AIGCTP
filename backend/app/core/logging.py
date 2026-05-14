"""Logging configuration for the application.

Production mode: JSON-structured logs for log-aggregator ingestion.
Development mode: Human-readable text format.

Both modes inject request_id, user_id, and session_id when available via the
request.state context (set by request_id_middleware in main.py).
"""
import json
import logging
import sys
from typing import Optional


_JSON_FORMAT: str = "json"
_TEXT_FORMAT: str = "text"


class RequestIdFilter(logging.Filter):
    """Inject request_id from the current request context into log records."""

    def __init__(self) -> None:
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        # These will be populated by middleware or can be set manually
        if not hasattr(record, "request_id"):
            record.request_id = ""
        if not hasattr(record, "user_id"):
            record.user_id = ""
        if not hasattr(record, "session_id"):
            record.session_id = ""
        if not hasattr(record, "correlation_id"):
            record.correlation_id = ""
        return True


class JsonFormatter(logging.Formatter):
    """Output log records as newline-delimited JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "") or "",
            "user_id": getattr(record, "user_id", "") or "",
            "session_id": getattr(record, "session_id", "") or "",
            "correlation_id": getattr(record, "correlation_id", "") or "",
        }
        if record.exc_info and record.exc_info[0]:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(debug: bool = False, app_env: Optional[str] = None) -> None:
    """Configure application-wide logging.

    Args:
        debug: Enable DEBUG-level logging.
        app_env: "production" enables JSON format.
    """
    level = logging.DEBUG if debug else logging.INFO
    is_json = app_env == "production"

    root = logging.getLogger("lifeai")
    root.setLevel(level)
    root.handlers.clear()
    request_filter = RequestIdFilter()
    root.addFilter(request_filter)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(request_filter)

    if is_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s  [req=%(request_id)s]",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    if is_json:
        root.info("JSON structured logging enabled", extra={"request_id": "", "user_id": "", "session_id": ""})


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name."""
    return logging.getLogger(f"lifeai.{name}")
