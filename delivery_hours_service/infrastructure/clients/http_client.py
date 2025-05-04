from contextlib import asynccontextmanager
from typing import ClassVar

import httpx
from httpx import AsyncClient, Response

from delivery_hours_service.common.logging import StructuredLogger

DEFAULT_TIMEOUT = 10.0  # seconds
DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=50)

logger = StructuredLogger(__name__)


class HttpClientError(Exception):
    """Base exception for all HTTP client errors"""

    pass


class ApiRequestError(HttpClientError):
    """Wrapper for HTTP errors with additional context"""

    def __init__(self, status_code: int, detail: str, *args):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}", *args)


class HttpClientPool:
    _clients: ClassVar[dict[str, AsyncClient]] = {}

    @classmethod
    def get_or_create_client(
        cls, base_url: str, timeout: float = DEFAULT_TIMEOUT
    ) -> AsyncClient:
        """
        Retrieve an existing AsyncClient instance for the given base URL
        or create a new one if it doesn't exist.
        This method implements a singleton pattern to maintain a single client
        instance per base URL.
        """

        if base_url not in cls._clients:
            logger.info(f"Creating new HTTP client for {base_url}")
            cls._clients[base_url] = AsyncClient(
                base_url=base_url, timeout=timeout, limits=DEFAULT_LIMITS, http2=True
            )
        return cls._clients[base_url]

    @classmethod
    async def close_all(cls):
        for base_url, client in cls._clients.items():
            logger.info(f"Closing HTTP client for {base_url}")
            await client.aclose()
        cls._clients.clear()


class HttpClient:
    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout

    async def get(self, endpoint: str, params: dict | None = None) -> Response:
        client = HttpClientPool.get_or_create_client(self.base_url, self.timeout)

        logger.debug(
            "Making HTTP request",
            operation="http_get",
            endpoint=endpoint,
            params=params,
        )

        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()

            logger.info(
                "HTTP request successful",
                operation="http_get",
                endpoint=endpoint,
                status_code=response.status_code,
            )
            return response
        except httpx.HTTPError as e:
            logger.error(
                "HTTP request failed",
                operation="http_get",
                endpoint=endpoint,
                detail=str(e),
                exc_info=True,
            )
            raise ApiRequestError(getattr(e, "status_code", 500), str(e)) from e


@asynccontextmanager
async def lifespan_http_clients(app):
    """
    Manages the lifespan of HTTP clients for the application.

    This asynchronous context manager ensures that all HTTP client connections
    are properly closed when the application shuts down.
    """

    try:
        yield
    finally:
        await HttpClientPool.close_all()
