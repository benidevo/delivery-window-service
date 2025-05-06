import asyncio
from dataclasses import dataclass, field

from delivery_hours_service.application.ports.courier_service import CourierServicePort
from delivery_hours_service.application.ports.venue_service import VenueServicePort
from delivery_hours_service.common.logging import StructuredLogger
from delivery_hours_service.common.resilience import CircuitBreakerError
from delivery_hours_service.domain.models.delivery_result import (
    DeliveryHoursResult,
    ErrorSeverity,
    ErrorSource,
)
from delivery_hours_service.domain.models.delivery_window import WeeklyDeliveryWindow
from delivery_hours_service.infrastructure.clients.http_client import ApiRequestError

logger = StructuredLogger(__name__)


@dataclass
class GetVenueDeliveryHoursUseCase:
    """
    Use case for retrieving and combining venue opening hours and
    courier delivery hours.

    This use case:
    1. Retrieves venue opening hours from VenueService
    2. Retrieves courier delivery hours from CourierService for the specified city
    3. Calculates the intersection of these hours to determine when
    deliveries are possible
    4. Returns the final delivery hours along with any errors or metadata
    """

    venue_service: VenueServicePort
    courier_service: CourierServicePort
    _service_type_to_error_source: dict = field(
        init=False,
        default_factory=lambda: {
            "venue": ErrorSource.VENUE_SERVICE,
            "courier": ErrorSource.COURIER_SERVICE,
        },
    )

    async def execute(self, venue_id: str, city_slug: str) -> DeliveryHoursResult:
        result = DeliveryHoursResult(delivery_window=WeeklyDeliveryWindow.empty())

        service_statuses: dict[str, str] = {}

        venue_hours, courier_hours = await self._get_hours_from_services(
            venue_id, city_slug, result, service_statuses
        )

        if venue_hours is None and courier_hours is None:
            return result

        if venue_hours is None:
            result.add_error(
                code="MISSING_VENUE_HOURS",
                source=ErrorSource.VENUE_SERVICE,
                severity=ErrorSeverity.ERROR,
            )
            return result

        if courier_hours is None:
            result.add_error(
                code="MISSING_COURIER_HOURS",
                source=ErrorSource.COURIER_SERVICE,
                severity=ErrorSeverity.ERROR,
            )
            return result

        try:
            delivery_hours = venue_hours.intersect_with(courier_hours)
            result.delivery_window = delivery_hours
        except Exception as e:
            logger.error(
                "Failed to calculate delivery hours intersection",
                error=str(e),
                error_type=type(e).__name__,
                venue_id=venue_id,
                city_slug=city_slug,
            )
            result.add_error(
                code="INTERSECTION_ERROR",
                source=ErrorSource.DOMAIN_LOGIC,
                severity=ErrorSeverity.ERROR,
                details={"error_type": type(e).__name__},
            )
            return result

        result.add_metadata("service_statuses", service_statuses)

        return result

    async def _get_hours_from_services(
        self,
        venue_id: str,
        city_slug: str,
        result: DeliveryHoursResult,
        service_statuses: dict[str, str],
    ) -> tuple[WeeklyDeliveryWindow | None, WeeklyDeliveryWindow | None]:
        venue_hours_task = asyncio.create_task(
            self.venue_service.get_opening_hours(venue_id)
        )
        courier_hours_task = asyncio.create_task(
            self.courier_service.get_delivery_hours(city_slug)
        )

        venue_task_result = await self._execute_task_safely(
            venue_hours_task, "venue", venue_id, result, service_statuses
        )
        courier_task_result = await self._execute_task_safely(
            courier_hours_task, "courier", city_slug, result, service_statuses
        )

        return venue_task_result, courier_task_result

    async def _execute_task_safely(
        self,
        task: asyncio.Task[WeeklyDeliveryWindow],
        service_type: str,
        identifier: str,
        result: DeliveryHoursResult,
        service_statuses: dict[str, str],
    ) -> WeeklyDeliveryWindow | None:
        error_source = self._service_type_to_error_source[service_type]
        service_status_key = f"{service_type}_service"

        try:
            service_result = await task
            service_statuses[service_status_key] = "success"
            return service_result

        except CircuitBreakerError as e:
            error_code = f"{service_type.upper()}_SERVICE_UNAVAILABLE"
            service_statuses[service_status_key] = "circuit_open"

            logger.error(
                f"Circuit breaker open for {service_type} service",
                error=str(e),
                service=service_type,
                identifier=identifier,
            )

            result.add_error(
                code=error_code,
                source=error_source,
                severity=ErrorSeverity.ERROR,
                details={"circuit_breaker": True},
            )
            return None

        except ApiRequestError as e:
            if e.status_code == 404:
                service_statuses[service_status_key] = "not_found"
                result.add_error(
                    code=f"{service_type.upper()}_NOT_FOUND",
                    source=error_source,
                    severity=ErrorSeverity.WARNING,
                )
                return WeeklyDeliveryWindow.empty()

            service_statuses[service_status_key] = f"api_error_{e.status_code}"
            result.add_error(
                code=f"{service_type.upper()}_SERVICE_ERROR",
                source=error_source,
                severity=ErrorSeverity.ERROR,
                details={"status_code": e.status_code},
            )
            return None

        except Exception as e:
            service_statuses[service_status_key] = "error"
            logger.error(
                f"Unexpected error getting {service_type} hours",
                error=str(e),
                error_type=type(e).__name__,
                service=service_type,
                identifier=identifier,
                exc_info=True,
            )
            result.add_error(
                code=f"{service_type.upper()}_SERVICE_ERROR",
                source=error_source,
                severity=ErrorSeverity.ERROR,
                details={"error_type": type(e).__name__},
            )
            return None
