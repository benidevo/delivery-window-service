from delivery_hours_service.domain.models.delivery_result import (
    DeliveryHoursResult,
    ErrorSeverity,
    ErrorSource,
)
from delivery_hours_service.domain.models.delivery_window import WeeklyDeliveryWindow


def test_should_create_empty_result_with_default_values() -> None:
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())

    assert result.delivery_window is not None
    assert result.delivery_window.is_empty()
    assert result.errors == []
    assert result.metadata == {}
    assert not result.has_errors
    assert not result.has_critical_errors


def test_should_indicate_has_errors_when_errors_exist() -> None:
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())

    assert not result.has_errors

    result.add_error(
        code="TEST_WARNING",
        message="Test warning",
        source=ErrorSource.UNKNOWN,
        severity=ErrorSeverity.WARNING,
    )

    assert result.has_errors
    assert not result.has_critical_errors


def test_should_detect_critical_errors() -> None:
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())

    result.add_error(
        code="TEST_WARNING",
        message="Test warning",
        source=ErrorSource.UNKNOWN,
        severity=ErrorSeverity.WARNING,
    )

    assert not result.has_critical_errors

    result.add_error(
        code="TEST_ERROR",
        message="Test error",
        source=ErrorSource.UNKNOWN,
        severity=ErrorSeverity.ERROR,
    )

    assert result.has_critical_errors


def test_should_create_success_result() -> None:
    delivery_window = WeeklyDeliveryWindow.empty()
    result = DeliveryHoursResult.success(
        delivery_window=delivery_window,
        processed_at="2023-01-01T12:00:00Z",
    )

    assert result.delivery_window is delivery_window
    assert result.errors == []
    assert result.metadata == {"processed_at": "2023-01-01T12:00:00Z"}


def test_should_create_error_result() -> None:
    result = DeliveryHoursResult.error(
        code="TEST_ERROR",
        message="Test error message",
        source=ErrorSource.VENUE_SERVICE,
        severity=ErrorSeverity.ERROR,
        details={"reason": "service unavailable"},
    )

    assert result.delivery_window.is_empty()
    assert len(result.errors) == 1
    assert result.errors[0].code == "TEST_ERROR"
    assert result.errors[0].message == "Test error message"
    assert result.errors[0].source == ErrorSource.VENUE_SERVICE
    assert result.errors[0].severity == ErrorSeverity.ERROR
    assert result.errors[0].details == {"reason": "service unavailable"}


def test_should_add_error_correctly() -> None:
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())

    result.add_error(
        code="ERROR_1",
        message="First error",
        source=ErrorSource.COURIER_SERVICE,
        severity=ErrorSeverity.WARNING,
    )

    result.add_error(
        code="ERROR_2",
        message="Second error",
        source=ErrorSource.DOMAIN_LOGIC,
        severity=ErrorSeverity.ERROR,
        details={"line": 42},
    )

    assert len(result.errors) == 2
    assert result.errors[0].code == "ERROR_1"
    assert result.errors[1].code == "ERROR_2"
    assert result.errors[1].details == {"line": 42}


def test_should_add_metadata_correctly() -> None:
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())

    result.add_metadata("processing_time_ms", 123)
    result.add_metadata("cache_hit", False)

    assert result.metadata == {
        "processing_time_ms": 123,
        "cache_hit": False,
    }

    result.add_metadata("processing_time_ms", 456)

    assert result.metadata["processing_time_ms"] == 456
