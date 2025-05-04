from fastapi import APIRouter, Depends, HTTPException, Query, status

from delivery_hours_service.application.use_cases.get_venue_delivery_hours import (
    GetVenueDeliveryHoursUseCase,
)
from delivery_hours_service.domain.models.delivery_result import (
    DeliveryHoursResult,
    ErrorSource,
)
from delivery_hours_service.domain.models.delivery_window import DayOfWeek
from delivery_hours_service.interface.api.dependencies import (
    get_delivery_hours_use_case,
)
from delivery_hours_service.interface.schemas.response import (
    DeliveryHoursResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/delivery-hours", tags=["delivery hours"])


def _format_hours(result: DeliveryHoursResult) -> dict[str, str]:
    """
    Formats the delivery hours from a DeliveryHoursResult
    object into a dictionary where:
    - Days with no delivery hours are marked as "Closed"
    - Hours are displayed without leading zeros (e.g., 9 instead of 09)
    - Minutes are only included if non-zero
        (e.g., "10:30" but just "10" for whole hours)
    - Multiple time windows on the same day are comma-separated
    """

    formatted_hours = {}
    schedule_data = result.delivery_window.get_schedule_data()

    for day in DayOfWeek:
        day_name = day.to_display_string()
        formatted_hours[day_name] = "Closed"

    for day, time_windows in schedule_data.items():
        if not time_windows:
            continue

        day_name = day.to_display_string()
        time_ranges = []

        for start_time, end_time in time_windows:
            start_str = str(start_time.hours)
            if start_time.minutes > 0:
                start_str += f":{start_time.minutes:02d}"

            end_str = str(end_time.hours)
            if end_time.minutes > 0:
                end_str += f":{end_time.minutes:02d}"

            time_ranges.append(f"{start_str}-{end_str}")

        formatted_hours[day_name] = ", ".join(time_ranges)

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
