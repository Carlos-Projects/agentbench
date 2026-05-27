"""JSON structured logging."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Logging formatter that outputs JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, str | int | float] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_json_logger(name: str = "agentbench") -> logging.Logger:
    """Set up a JSON-structured logger.

    Args:
        name: Logger name.

    Returns:
        Configured logger.
    """
    _logger = logging.getLogger(name)
    for handler in _logger.handlers[:]:
        _logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

    return _logger
