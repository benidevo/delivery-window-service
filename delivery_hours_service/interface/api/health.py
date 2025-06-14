from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint that verifies basic system status.
    """
    health_status = {
        "status": "healthy",
        "service": "delivery-hours-service",
        "version": "1.0.0",
    }

    return JSONResponse(content=health_status, status_code=200)
