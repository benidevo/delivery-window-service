from fastapi import APIRouter, Depends, HTTPException, Query, status

from delivery_hours_service.application.use_cases.get_venue_delivery_hours import (
    GetVenueDeliveryHoursUseCase,
)
from delivery_hours_service.domain.models.delivery_result import (
    ErrorSource,
)
from delivery_hours_service.interface.api.dependencies import (
    get_delivery_hours_use_case,
)
from delivery_hours_service.interface.schemas.response import (
    DeliveryHoursResponse,
    ErrorResponse,
    Weekday,
)

router = APIRouter(prefix="/delivery-hours", tags=["delivery hours"])


def _format_hours(result):
    """Format delivery hours for API response."""
    formatted_hours = {}

    for day_enum in Weekday:
        day_name = day_enum.name.capitalize()
        formatted_hours[day_name] = "Closed"

    for day_data in result.to_day_schedules():
        day_name = day_data["day"].capitalize()

        time_ranges_formatted = []
        for time_data in day_data["times"]:
            start_parts = time_data["start"].split(":")
            end_parts = time_data["end"].split(":")

            start_formatted = (
                start_parts[0].lstrip("0") if start_parts[0] != "00" else "0"
            )
            if start_parts[1] != "00":
                start_formatted += ":" + start_parts[1]

            end_formatted = end_parts[0].lstrip("0") if end_parts[0] != "00" else "0"
            if end_parts[1] != "00":
                end_formatted += ":" + end_parts[1]

            time_ranges_formatted.append(f"{start_formatted}-{end_formatted}")

        formatted_hours[day_name] = ", ".join(time_ranges_formatted)

    return formatted_hours


def _raise_appropriate_exception(result) -> None:
    """
    Ensures errors are mapped to appropriate status codes without
    leaking implementation details.
    """
    if not result.has_errors:
        return

    for error in result.errors:
        if error.code in [
            "VENUE_SERVICE_UNAVAILABLE",
            "COURIER_SERVICE_UNAVAILABLE",
            "VENUE_SERVICE_ERROR",
            "COURIER_SERVICE_ERROR",
        ]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

        if error.source == ErrorSource.DOMAIN_LOGIC:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to process delivery hours",
            )

    if result.has_critical_errors:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request",
        )


@router.get(
    "",
    response_model=DeliveryHoursResponse,
    responses={
        200: {
            "model": DeliveryHoursResponse,
            "description": "Successful response with delivery hours",
        },
        503: {"model": ErrorResponse, "description": "External service unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_delivery_hours(
    city_slug: str = Query(
        ...,
        description="City identifier used to retrieve courier availability "
        "in that area",
    ),
    venue_id: str = Query(
        ...,
        description="Unique identifier of the venue to get opening hours for",
    ),
    use_case: GetVenueDeliveryHoursUseCase = Depends(  # noqa: B008
        get_delivery_hours_use_case
    ),
):
    """
    Retrieve delivery hours for a specific venue in a given city.

    This endpoint provides the delivery hours for a venue, allowing clients to
    determine when delivery is available based on courier availability
    and venue opening hours.
    """
    result = await use_case.execute(venue_id=venue_id, city_slug=city_slug)

    _raise_appropriate_exception(result)

    formatted_hours = _format_hours(result)
    return DeliveryHoursResponse(delivery_hours=formatted_hours)
