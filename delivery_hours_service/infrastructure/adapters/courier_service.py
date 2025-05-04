from datetime import timedelta

from delivery_hours_service.application.ports.courier_service import CourierServicePort
from delivery_hours_service.common.config import ServiceConfig
from delivery_hours_service.common.logging import StructuredLogger
from delivery_hours_service.common.resilience import (
    CircuitBreakerConfig,
    CircuitBreakerError,
    circuit_breaker,
)
from delivery_hours_service.domain.models.delivery_window import WeeklyDeliveryWindow
from delivery_hours_service.infrastructure.clients.http_client import (
    ApiRequestError,
    HttpClient,
)
from delivery_hours_service.infrastructure.converters.time_windows_converter import (
    TimeWindowsConverter,
)

logger = StructuredLogger(__name__)


class CourierServiceAdapter(CourierServicePort):
    def __init__(self, config: ServiceConfig, client: HttpClient | None = None):
        self.client = client or HttpClient(config.courier_service_url)

    @circuit_breaker(CircuitBreakerConfig(reset_timeout=timedelta(seconds=30)))
    async def get_delivery_hours(self, city: str) -> WeeklyDeliveryWindow:
        """
        Retrieves delivery hours for a city from the Courier Service and
        converts them to the domain representation.
        """
        logger.info(f"Fetching delivery hours for city {city}")

        try:
            response = await self.client.get("/delivery-hours", {"city": city})
            data = response.json()

            return TimeWindowsConverter.convert_to_weekly_delivery_window(data)
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker is open for courier service: {str(e)}")
            raise
        except ApiRequestError as e:
            if e.status_code == 404:
                logger.warning(
                    f"City {city} not found in courier service",
                    error_code="CITY_NOT_FOUND",
                    city=city,
                    status_code=e.status_code,
                )
                return WeeklyDeliveryWindow.empty()
            logger.error(f"Failed to fetch delivery hours for city {city}: {str(e)}")
            raise
        except Exception:
            logger.error(
                f"Unexpected error fetching delivery hours for city {city}",
                exc_info=True,
            )
            raise
