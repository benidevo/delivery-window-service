from unittest.mock import patch

import pytest

from delivery_hours_service.application.ports.courier_service import CourierServicePort
from delivery_hours_service.application.ports.venue_service import VenueServicePort
from delivery_hours_service.application.use_cases.get_venue_delivery_hours import (
    GetVenueDeliveryHoursUseCase,
)
from delivery_hours_service.common.resilience import CircuitBreakerError
from delivery_hours_service.domain.models.delivery_result import (
    ErrorSeverity,
    ErrorSource,
)
from delivery_hours_service.domain.models.delivery_window import (
    DayOfWeek,
    DeliveryWindow,
    WeeklyDeliveryWindow,
)
from delivery_hours_service.domain.models.time import Time, TimeRange
from delivery_hours_service.infrastructure.clients.http_client import ApiRequestError


class MockVenueService(VenueServicePort):
    def __init__(self, response=None, error=None):
        self.response = response or WeeklyDeliveryWindow.empty()
        self.error = error
        self.called_with = None

    async def get_opening_hours(self, venue_id: str) -> WeeklyDeliveryWindow:
        self.called_with = venue_id
        if self.error:
            raise self.error
        return self.response


class MockCourierService(CourierServicePort):
    def __init__(self, response=None, error=None):
        self.response = response or WeeklyDeliveryWindow.empty()
        self.error = error
        self.called_with = None

    async def get_delivery_hours(self, city: str) -> WeeklyDeliveryWindow:
        self.called_with = city
        if self.error:
            raise self.error
        return self.response


@pytest.fixture
def mock_venue_service() -> MockVenueService:
    return MockVenueService()


@pytest.fixture
def mock_courier_service() -> MockCourierService:
    return MockCourierService()


@pytest.fixture
def use_case(mock_venue_service, mock_courier_service) -> GetVenueDeliveryHoursUseCase:
    return GetVenueDeliveryHoursUseCase(
        venue_service=mock_venue_service,
        courier_service=mock_courier_service,
    )


def create_delivery_window(day: DayOfWeek, hours_list) -> DeliveryWindow:
    windows = [TimeRange(Time(start, 0), Time(end, 0)) for start, end in hours_list]
    return DeliveryWindow(day=day, windows=windows)


def create_weekly_window(day_hours_map) -> WeeklyDeliveryWindow:
    schedule = {}
    for day_name, hours_list in day_hours_map.items():
        day = getattr(DayOfWeek, day_name.upper())
        schedule[day] = create_delivery_window(day, hours_list)

    return WeeklyDeliveryWindow(schedule)


@pytest.mark.asyncio
async def test_should_call_services_with_correct_parameters(use_case) -> None:
    await use_case.execute(venue_id="venue-123", city_slug="helsinki")

    assert use_case.venue_service.called_with == "venue-123"
    assert use_case.courier_service.called_with == "helsinki"


@pytest.mark.asyncio
async def test_should_return_intersection_of_venue_and_courier_hours(
    use_case, mock_venue_service, mock_courier_service
) -> None:
    # (10-14, 16-22 on Monday)
    mock_venue_service.response = create_weekly_window(
        {
            "monday": [(10, 14), (16, 22)],
        }
    )

    # (9-13, 15-21 on Monday)
    mock_courier_service.response = create_weekly_window(
        {
            "monday": [(9, 13), (15, 21)],
        }
    )

    result = await use_case.execute(venue_id="venue-123", city_slug="helsinki")

    monday_window = result.delivery_window.get_day_window(DayOfWeek.MONDAY)

    assert not result.has_errors
    assert len(monday_window.windows) == 2

    # First window should be 10-13 (intersection of 10-14 and 9-13)
    assert monday_window.windows[0].start_time.hours == 10
    assert monday_window.windows[0].end_time.hours == 13

    # Second window should be 16-21 (intersection of 16-22 and 15-21)
    assert monday_window.windows[1].start_time.hours == 16
    assert monday_window.windows[1].end_time.hours == 21


@pytest.mark.asyncio
async def test_should_handle_venue_service_404_error(
    use_case, mock_venue_service
) -> None:
    mock_venue_service.error = ApiRequestError(404, "Venue not found")

    result = await use_case.execute(venue_id="invalid-venue", city_slug="helsinki")

    assert result.has_errors
    assert len(result.errors) == 1
    assert result.errors[0].code == "VENUE_NOT_FOUND"
    assert result.errors[0].severity == ErrorSeverity.WARNING
    assert result.errors[0].source == ErrorSource.VENUE_SERVICE

    assert result.delivery_window.is_empty()


@pytest.mark.asyncio
async def test_should_handle_courier_service_404_error(
    use_case, mock_courier_service
) -> None:
    mock_courier_service.error = ApiRequestError(404, "City not found")

    result = await use_case.execute(venue_id="venue-123", city_slug="invalid-city")

    assert result.has_errors
    assert len(result.errors) == 1
    assert result.errors[0].code == "COURIER_NOT_FOUND"
    assert result.errors[0].severity == ErrorSeverity.WARNING
    assert result.errors[0].source == ErrorSource.COURIER_SERVICE

    assert result.delivery_window.is_empty()


@pytest.mark.asyncio
async def test_should_handle_venue_service_circuit_breaker_error(
    use_case, mock_venue_service
) -> None:
    mock_venue_service.error = CircuitBreakerError("Circuit breaker is open")

    result = await use_case.execute(venue_id="venue-123", city_slug="helsinki")

    assert result.has_errors
    assert result.has_critical_errors
    # First error from circuit breaker, second from missing hours
    assert len(result.errors) == 2

    assert result.errors[0].code == "VENUE_SERVICE_UNAVAILABLE"
    assert result.errors[0].severity == ErrorSeverity.ERROR
    assert (
        result.errors[0].details is not None
        and result.errors[0].details.get("circuit_breaker") is True
    )

    assert result.errors[1].code == "MISSING_VENUE_HOURS"
    assert result.errors[1].severity == ErrorSeverity.ERROR

    assert result.delivery_window.is_empty()


@pytest.mark.asyncio
async def test_should_handle_courier_service_circuit_breaker_error(
    use_case, mock_courier_service
) -> None:
    mock_courier_service.error = CircuitBreakerError("Circuit breaker is open")

    result = await use_case.execute(venue_id="venue-123", city_slug="helsinki")

    assert result.has_errors
    assert result.has_critical_errors
    # First error from circuit breaker, second from missing hours
    assert len(result.errors) == 2

    assert result.errors[0].code == "COURIER_SERVICE_UNAVAILABLE"
    assert result.errors[0].severity == ErrorSeverity.ERROR
    assert (
        result.errors[0].details is not None
        and result.errors[0].details.get("circuit_breaker") is True
    )

    assert result.errors[1].code == "MISSING_COURIER_HOURS"
    assert result.errors[1].severity == ErrorSeverity.ERROR

    assert result.delivery_window.is_empty()


@pytest.mark.asyncio
async def test_should_handle_venue_service_api_error(
    use_case, mock_venue_service
) -> None:
    mock_venue_service.error = ApiRequestError(500, "Internal server error")

    result = await use_case.execute(venue_id="venue-123", city_slug="helsinki")

    assert result.has_errors
    assert result.has_critical_errors
    # First from API error, second from missing hours
    assert len(result.errors) == 2

    assert result.errors[0].code == "VENUE_SERVICE_ERROR"
    assert result.errors[0].severity == ErrorSeverity.ERROR
    assert (
        result.errors[0].details is not None
        and "status_code" in result.errors[0].details
    )

    assert result.errors[1].code == "MISSING_VENUE_HOURS"
    assert result.errors[1].severity == ErrorSeverity.ERROR

    assert result.delivery_window.is_empty()


@pytest.mark.asyncio
async def test_should_handle_courier_service_api_error(
    use_case, mock_courier_service
) -> None:
    mock_courier_service.error = ApiRequestError(500, "Internal server error")

    result = await use_case.execute(venue_id="venue-123", city_slug="helsinki")

    assert result.has_errors
    assert result.has_critical_errors
    # First from API error, second from missing hours
    assert len(result.errors) == 2

    assert result.errors[0].code == "COURIER_SERVICE_ERROR"
    assert result.errors[0].severity == ErrorSeverity.ERROR
    assert (
        result.errors[0].details is not None
        and "status_code" in result.errors[0].details
    )

    assert result.errors[1].code == "MISSING_COURIER_HOURS"
    assert result.errors[1].severity == ErrorSeverity.ERROR

    assert result.delivery_window.is_empty()


@pytest.mark.asyncio
async def test_should_handle_both_services_failing(
    use_case, mock_venue_service, mock_courier_service
) -> None:
    mock_venue_service.error = ApiRequestError(500, "Venue service error")
    mock_courier_service.error = ApiRequestError(500, "Courier service error")

    result = await use_case.execute(venue_id="venue-123", city_slug="helsinki")

    assert result.has_errors
    assert result.has_critical_errors
    assert len(result.errors) == 2

    error_codes = [error.code for error in result.errors]
    assert "VENUE_SERVICE_ERROR" in error_codes
    assert "COURIER_SERVICE_ERROR" in error_codes

    assert result.delivery_window.is_empty()


@pytest.mark.asyncio
async def test_should_handle_intersect_with_error(
    use_case, mock_venue_service, mock_courier_service
) -> None:
    mock_venue_service.response = create_weekly_window(
        {
            "monday": [(10, 14)],
        }
    )
    mock_courier_service.response = create_weekly_window(
        {
            "monday": [(12, 16)],
        }
    )

    with patch.object(
        WeeklyDeliveryWindow,
        "intersect_with",
        side_effect=Exception("Intersection error"),
    ):
        result = await use_case.execute(venue_id="venue-123", city_slug="helsinki")

    assert result.has_errors
    assert result.has_critical_errors
    assert len(result.errors) == 1
    assert result.errors[0].code == "INTERSECTION_ERROR"
    assert result.errors[0].source == ErrorSource.DOMAIN_LOGIC
