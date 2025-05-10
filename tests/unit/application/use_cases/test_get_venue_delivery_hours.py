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
async def test_get_venue_delivery_hours_use_case(
    use_case, mock_venue_service, mock_courier_service
) -> None:
    await use_case.execute(venue_id="venue-123", city_slug="helsinki")
    assert use_case.venue_service.called_with == "venue-123"
    assert use_case.courier_service.called_with == "helsinki"

    # Test successful intersection calculation
    mock_venue_service.response = create_weekly_window(
        {
            "monday": [(10, 14), (16, 22)],
        }
    )
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

    assert monday_window.windows[1].start_time.hours == 16
    assert monday_window.windows[1].end_time.hours == 21

    # Test error handling
    # Reset responses
    mock_venue_service.response = WeeklyDeliveryWindow.empty()
    mock_courier_service.response = WeeklyDeliveryWindow.empty()

    mock_venue_service.error = ApiRequestError(404, "Venue not found")
    mock_courier_service.error = None

    result = await use_case.execute(venue_id="invalid-venue", city_slug="helsinki")
    assert result.has_errors
    assert len(result.errors) == 1
    assert result.errors[0].code == "VENUE_NOT_FOUND"
    assert result.errors[0].severity == ErrorSeverity.WARNING
    assert result.errors[0].source == ErrorSource.VENUE_SERVICE
    assert result.delivery_window.is_empty()

    # Test 404 error from courier service
    mock_venue_service.error = None
    mock_courier_service.error = ApiRequestError(404, "City not found")

    result = await use_case.execute(venue_id="venue-123", city_slug="invalid-city")
    assert result.has_errors
    assert len(result.errors) == 1
    assert result.errors[0].code == "COURIER_NOT_FOUND"
    assert result.errors[0].severity == ErrorSeverity.WARNING
    assert result.errors[0].source == ErrorSource.COURIER_SERVICE
    assert result.delivery_window.is_empty()

    mock_venue_service.error = CircuitBreakerError("Circuit breaker is open")
    mock_courier_service.error = None

    result = await use_case.execute(venue_id="venue-123", city_slug="helsinki")
    assert result.has_errors
    assert result.has_critical_errors
    assert "VENUE_SERVICE_UNAVAILABLE" in [e.code for e in result.errors]
    assert result.delivery_window.is_empty()

    mock_venue_service.error = None
    mock_courier_service.error = None
    mock_venue_service.response = create_weekly_window({"monday": [(10, 14)]})
    mock_courier_service.response = create_weekly_window({"monday": [(12, 16)]})

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
