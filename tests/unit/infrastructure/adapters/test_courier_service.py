from unittest.mock import AsyncMock

import pytest

from delivery_hours_service.common.config import ServiceConfig
from delivery_hours_service.common.resilience import CircuitBreakerError
from delivery_hours_service.infrastructure.adapters.courier_service import (
    CourierServiceAdapter,
)
from delivery_hours_service.infrastructure.clients.http_client import ApiRequestError


@pytest.fixture
def service_config() -> ServiceConfig:
    return ServiceConfig(
        venue_service_url="http://test-venue-service",
        courier_service_url="http://test-courier-service",
        redis_url="redis://localhost:6379",
        cache_ttl_seconds=300,
    )


@pytest.fixture
def mock_http_client() -> AsyncMock:
    client = AsyncMock()
    client.get = AsyncMock()
    return client


@pytest.fixture
def courier_service_adapter(service_config, mock_http_client) -> CourierServiceAdapter:
    return CourierServiceAdapter(service_config, client=mock_http_client)


@pytest.mark.asyncio
async def test_get_delivery_hours_should_call_courier_service_with_correct_parameters(
    courier_service_adapter, mock_http_client
) -> None:
    mock_response = AsyncMock()
    mock_http_client.get.return_value = mock_response

    response_data: dict = {"monday": []}
    mock_response.json = lambda: response_data

    await courier_service_adapter.get_delivery_hours("helsinki")

    mock_http_client.get.assert_called_once_with(
        "/delivery-hours", {"city": "helsinki"}
    )


@pytest.mark.asyncio
async def test_get_delivery_hours_should_propagate_404_error(
    courier_service_adapter, mock_http_client
) -> None:
    mock_http_client.get.side_effect = ApiRequestError(404, "City not found")

    with pytest.raises(ApiRequestError) as exc_info:
        await courier_service_adapter.get_delivery_hours("unknown-city")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_delivery_hours_should_propagate_circuit_breaker_error(
    courier_service_adapter, mock_http_client
) -> None:
    mock_http_client.get.side_effect = CircuitBreakerError("Circuit breaker is open")

    with pytest.raises(CircuitBreakerError):
        await courier_service_adapter.get_delivery_hours("helsinki")


@pytest.mark.asyncio
async def test_get_delivery_hours_should_propagate_api_errors(
    courier_service_adapter, mock_http_client
) -> None:
    mock_http_client.get.side_effect = ApiRequestError(500, "Server error")

    with pytest.raises(ApiRequestError):
        await courier_service_adapter.get_delivery_hours("helsinki")
