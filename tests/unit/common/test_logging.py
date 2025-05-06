import json
import logging
from io import StringIO

import pytest

from delivery_hours_service.common.logging import LogLevel, StructuredLogger


def test_log_level_values_match_logging_module() -> None:
    assert LogLevel.DEBUG.value == logging.DEBUG
    assert LogLevel.INFO.value == logging.INFO
    assert LogLevel.WARNING.value == logging.WARNING
    assert LogLevel.ERROR.value == logging.ERROR
    assert LogLevel.CRITICAL.value == logging.CRITICAL


@pytest.fixture
def mock_stream() -> StringIO:
    return StringIO()


@pytest.fixture
def configured_logger(mock_stream: StringIO) -> StructuredLogger:
    handler = logging.StreamHandler(mock_stream)

    logger = StructuredLogger("configured_logger")
    logger.logger.handlers = []
    logger.logger.addHandler(handler)
    logger.logger.setLevel(logging.DEBUG)

    return logger


def test_should_initialize_with_correct_name() -> None:
    logger = StructuredLogger("test_name")
    assert logger.logger.name == "test_name"


def test_should_add_stream_handler_when_initialized() -> None:
    logger = StructuredLogger("configured_logger")
    assert any(
        isinstance(handler, logging.StreamHandler) for handler in logger.logger.handlers
    )


def test_should_format_log_entry_as_json_with_correct_fields(
    configured_logger: StructuredLogger, mock_stream: StringIO
) -> None:
    configured_logger.info("test_message", key="value")

    log_output = mock_stream.getvalue()
    log_data = json.loads(log_output.strip())

    assert log_data["message"] == "test_message"
    assert log_data["level"] == "info"
    assert log_data["service"] == "delivery_hours_service"
    assert log_data["key"] == "value"
    assert "timestamp" in log_data


@pytest.mark.parametrize(
    "log_method,expected_level",
    [
        ("debug", "debug"),
        ("info", "info"),
        ("warning", "warning"),
        ("error", "error"),
        ("critical", "critical"),
    ],
)
def test_should_log_with_appropriate_level(
    configured_logger: StructuredLogger,
    mock_stream: StringIO,
    log_method: str,
    expected_level: str,
) -> None:
    mock_stream.truncate(0)
    mock_stream.seek(0)

    getattr(configured_logger, log_method)("test_message")

    log_output = mock_stream.getvalue()
    log_data = json.loads(log_output.strip())

    assert log_data["level"] == expected_level
