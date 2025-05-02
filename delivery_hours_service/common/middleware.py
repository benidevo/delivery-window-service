from fastapi import Request
from fastapi.responses import JSONResponse

from delivery_hours_service.common.logging import StructuredLogger

logger = StructuredLogger(__name__)


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
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            },
        )
