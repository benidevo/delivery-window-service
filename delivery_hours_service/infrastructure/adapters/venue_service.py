from datetime import timedelta

from delivery_hours_service.application.ports.venue_service import VenueServicePort
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


class VenueServiceAdapter(VenueServicePort):
    def __init__(self, config: ServiceConfig, client: HttpClient | None = None):
        self.client = client or HttpClient(config.venue_service_url)

    @circuit_breaker(CircuitBreakerConfig(reset_timeout=timedelta(seconds=30)))
    async def get_opening_hours(self, venue_id: str) -> WeeklyDeliveryWindow:
        """
        Retrieves opening hours for a venue from the Venue Service and
        converts them to the domain representation.
        """
        logger.info(f"Fetching opening hours for venue {venue_id}")

        try:
            endpoint = f"/venues/{venue_id}/opening-hours"
            response = await self.client.get(endpoint)
            data = response.json()

            return TimeWindowsConverter.convert_to_weekly_delivery_window(data)
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker is open for venue service: {str(e)}")
            raise
        except ApiRequestError as e:
            if e.status_code == 404:
                logger.warning(
                    f"Venue {venue_id} not found in venue service",
                    error_code="VENUE_NOT_FOUND",
                    venue_id=venue_id,
                    status_code=e.status_code,
                )
            else:
                logger.error(
                    f"Failed to fetch opening hours for venue {venue_id}: {str(e)}"
                )
            raise
        except Exception:
            logger.error(
                f"Unexpected error fetching opening hours for venue {venue_id}",
                exc_info=True,
            )
            raise
