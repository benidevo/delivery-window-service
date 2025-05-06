from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from delivery_hours_service.infrastructure.clients.http_client import (
    HttpClient,
    HttpClientPool,
)


def test_http_client_should_be_initialized_with_custom_values():
    client = HttpClient("https://test-api.com", timeout=15.0)
    assert client.base_url == "https://test-api.com"
    assert client.timeout == 15.0


def test_http_client_should_use_default_values_when_not_specified():
    client = HttpClient("https://test-api.com")
    assert client.base_url == "https://test-api.com"
    assert client.timeout == 10.0


@pytest.mark.asyncio
async def test_http_client_pool_should_create_and_reuse_connections():
    # Clear any existing clients
    HttpClientPool._clients = {}

    with patch(
        "delivery_hours_service.infrastructure.clients.http_client.AsyncClient"
    ) as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        client1 = HttpClientPool.get_or_create_client("https://test-api.com")
        assert client1 == mock_instance
        assert len(HttpClientPool._clients) == 1
        mock_client.assert_called_once()

        client2 = HttpClientPool.get_or_create_client("https://test-api.com")
        assert client2 == mock_instance
        assert len(HttpClientPool._clients) == 1
        mock_client.assert_called_once()

        HttpClientPool.get_or_create_client("https://another-api.com")
        assert len(HttpClientPool._clients) == 2
        assert mock_client.call_count == 2


@pytest.mark.asyncio
async def test_http_client_pool_should_close_all_clients_on_shutdown():
    mock_client1 = AsyncMock()
    mock_client2 = AsyncMock()

    # Ensure aclose is a coroutine that returns None
    mock_client1.aclose.return_value = None
    mock_client2.aclose.return_value = None

    HttpClientPool._clients = {
        "https://api1.com": mock_client1,
        "https://api2.com": mock_client2,
    }

    await HttpClientPool.close_all()

    mock_client1.aclose.assert_called_once()
    mock_client2.aclose.assert_called_once()
    assert HttpClientPool._clients == {}
