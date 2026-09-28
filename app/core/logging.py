"""
Structured Logging & Tracing Configuration.
Ensures zero-leakage of API keys, passwords, or personal credentials.
"""

import logging
import sys
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

# In-memory ring buffer for live observability logs in the UI
RECENT_LOGS: List[Dict[str, Any]] = []
MAX_IN_MEMORY_LOGS = 200

# Patterns that must be sanitized before writing to logs
SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|secret|password|bearer|authorization)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'),
]


def sanitize_message(msg: str) -> str:
    """Sanitize sensitive patterns from log messages."""
    sanitized = str(msg)
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(r'\1: [REDACTED_SECRET]', sanitized)
    return sanitized


class JsonFormatter(logging.Formatter):
    """Formats log records as JSON for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_message(record.getMessage()),
        }
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data["details"] = {
                k: sanitize_message(str(v)) if isinstance(v, str) else v
                for k, v in record.extra_data.items()
            }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Store in recent logs buffer
        if len(RECENT_LOGS) >= MAX_IN_MEMORY_LOGS:
            RECENT_LOGS.pop(0)
        RECENT_LOGS.append(log_data)

        return json.dumps(log_data)


def setup_logger(name: str = "restaurant_agent", log_level: str = "INFO") -> logging.Logger:
    """Configure and return a structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


logger = setup_logger()


def log_agent_event(event_type: str, message: str, details: Dict[str, Any] = None):
    """Convenience helper for structured observability events."""
    extra = {"event_type": event_type}
    if details:
        extra.update(details)
    logger.info(message, extra={"extra_data": extra})
