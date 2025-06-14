import uuid
from contextvars import ContextVar

from fastapi import Request
from fastapi.responses import JSONResponse

from delivery_hours_service.common.logging import StructuredLogger

logger = StructuredLogger(__name__)

# Context variable to store correlation ID across async calls
correlation_id_context: ContextVar[str] = ContextVar("correlation_id", default="")


async def correlation_id_middleware(request: Request, call_next):
    """
    Middleware to handle request correlation IDs.

    Extracts or generates a correlation ID for each request and makes it
    available throughout the request lifecycle through context variables.
    """
    correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    correlation_id_context.set(correlation_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = correlation_id

    return response


async def error_handling_middleware(request: Request, call_next) -> JSONResponse:
    """
    This middleware catches any unhandled exceptions that occur during request
    processing, logs the error details, and returns a standardized 500
    Internal Server Error response to the client.
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__,
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "An unexpected error occurred",
            },
        )
