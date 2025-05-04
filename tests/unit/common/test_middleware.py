import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from delivery_hours_service.common.middleware import (
    error_handling_middleware,
)


@pytest.fixture
def mock_request() -> MagicMock:
    request = MagicMock(spec=Request)
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.url = MagicMock()
    request.url.path = "/test-path"
    request.method = "GET"
    return request


@pytest.mark.asyncio
async def test_error_handling_middleware_should_pass_response_when_no_exception(
    mock_request: MagicMock,
) -> None:
    expected_response = JSONResponse(status_code=200, content={"status": "ok"})
    mock_call_next = AsyncMock(return_value=expected_response)

    response = await error_handling_middleware(mock_request, mock_call_next)

    assert response == expected_response
    mock_call_next.assert_called_once_with(mock_request)


@pytest.mark.asyncio
async def test_error_handling_middleware_should_return_500_when_exception_raised(
    mock_request: MagicMock,
) -> None:
    mock_call_next = AsyncMock(side_effect=ValueError("Test error"))

    response = await error_handling_middleware(mock_request, mock_call_next)

    assert response.status_code == 500
    assert json.loads(response.body)["detail"] == "An unexpected error occurred"
    mock_call_next.assert_called_once_with(mock_request)
