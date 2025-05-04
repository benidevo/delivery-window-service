import pytest
from fastapi import HTTPException

from delivery_hours_service.domain.models.delivery_result import (
    DeliveryHoursResult,
    ErrorSeverity,
    ErrorSource,
)
from delivery_hours_service.domain.models.delivery_window import (
    WeeklyDeliveryWindow,
)
from delivery_hours_service.interface.api.delivery_hours_api import (
    _format_hours,
    _raise_appropriate_exception,
)


def test_should_format_empty_result_as_all_closed():
    empty_result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())

    formatted_hours = _format_hours(empty_result)

    for day in [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]:
        assert day in formatted_hours
        assert formatted_hours[day] == "Closed"


def test_should_not_raise_exception_when_no_errors():
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())

    _raise_appropriate_exception(result)


def test_should_raise_503_when_service_unavailable():
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())
    result.add_error(
        code="COURIER_SERVICE_UNAVAILABLE",
        source=ErrorSource.COURIER_SERVICE,
        severity=ErrorSeverity.ERROR,
    )

    with pytest.raises(HTTPException) as exc_info:
        _raise_appropriate_exception(result)

    assert exc_info.value.status_code == 503
    assert "service temporarily unavailable" in exc_info.value.detail.lower()


def test_should_raise_500_when_domain_logic_error():
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())
    result.add_error(
        code="INTERSECTION_ERROR",
        source=ErrorSource.DOMAIN_LOGIC,
        severity=ErrorSeverity.ERROR,
    )

    with pytest.raises(HTTPException) as exc_info:
        _raise_appropriate_exception(result)

    assert exc_info.value.status_code == 500
    assert "unable to process delivery hours" in exc_info.value.detail.lower()


def test_should_raise_500_when_critical_error():
    result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())
    result.add_error(
        code="UNKNOWN_ERROR",
        source=ErrorSource.UNKNOWN,
        severity=ErrorSeverity.ERROR,  # Critical error
    )

    with pytest.raises(HTTPException) as exc_info:
        _raise_appropriate_exception(result)

    assert exc_info.value.status_code == 500
