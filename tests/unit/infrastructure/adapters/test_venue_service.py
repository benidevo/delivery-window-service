from unittest.mock import AsyncMock

import pytest

from delivery_hours_service.common.config import ServiceConfig
from delivery_hours_service.common.resilience import CircuitBreakerError
from delivery_hours_service.infrastructure.adapters.venue_service import (
    VenueServiceAdapter,
)
from delivery_hours_service.infrastructure.clients.http_client import ApiRequestError


@pytest.fixture
def venue_service_config() -> ServiceConfig:
    return ServiceConfig(
        venue_service_url="http://test-venue-service",
        courier_service_url="http://test-courier-service",
    )


@pytest.fixture
def mock_http_client() -> AsyncMock:
    client = AsyncMock()
    client.get = AsyncMock()
    return client


@pytest.fixture
def venue_service_adapter(
    venue_service_config, mock_http_client
) -> VenueServiceAdapter:
    """Returns a VenueServiceAdapter with mocked dependencies for testing."""
    return VenueServiceAdapter(venue_service_config, client=mock_http_client)


@pytest.mark.asyncio
async def test_get_opening_hours_should_call_venue_service_with_correct_endpoint(
    venue_service_adapter, mock_http_client
) -> None:
    mock_response = AsyncMock()
    mock_http_client.get.return_value = mock_response

    response_data: dict = {"monday": []}
    # Make json() a regular Mock, not AsyncMock
    mock_response.json = lambda: response_data

    # Call the adapter method
    await venue_service_adapter.get_opening_hours("123")

    # Verify the HTTP client was called correctly
    mock_http_client.get.assert_called_once_with("/venues/123/opening-hours")


@pytest.mark.asyncio
async def test_get_opening_hours_should_propagate_404_error(
    venue_service_adapter, mock_http_client
) -> None:
    mock_http_client.get.side_effect = ApiRequestError(404, "Venue not found")

    with pytest.raises(ApiRequestError) as exc_info:
        await venue_service_adapter.get_opening_hours("invalid-id")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_opening_hours_should_propagate_circuit_breaker_error(
    venue_service_adapter, mock_http_client
) -> None:
    mock_http_client.get.side_effect = CircuitBreakerError("Circuit breaker is open")

    with pytest.raises(CircuitBreakerError):
        await venue_service_adapter.get_opening_hours("123")


@pytest.mark.asyncio
async def test_get_opening_hours_should_propagate_api_errors(
    venue_service_adapter, mock_http_client
) -> None:
    mock_http_client.get.side_effect = ApiRequestError(500, "Server error")

    with pytest.raises(ApiRequestError):
        await venue_service_adapter.get_opening_hours("123")
