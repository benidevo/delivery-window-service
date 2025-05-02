import json
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_formatter()

    def _setup_formatter(self):
        log_handler = logging.StreamHandler()
        if not any(
            isinstance(handler, logging.StreamHandler)
            for handler in self.logger.handlers
        ):
            self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)

    def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "delivery_hours_service",
            "message": message,
            "level": level.name.lower(),
            **context,
        }
        self.logger.log(level.value, json.dumps(log_entry))

    def info(self, message: str, **context: Any) -> None:
        self._log(LogLevel.INFO, message, **context)

    def debug(self, message: str, **context: Any) -> None:
        self._log(LogLevel.DEBUG, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        self._log(LogLevel.WARNING, message, **context)

    def critical(self, message: str, **context: Any) -> None:
        self._log(LogLevel.CRITICAL, message, **context)

    def error(self, message: str, **context: Any) -> None:
        self._log(LogLevel.ERROR, message, **context)
