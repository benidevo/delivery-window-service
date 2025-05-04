from functools import lru_cache

from fastapi import Depends

from delivery_hours_service.application.ports.courier_service import CourierServicePort
from delivery_hours_service.application.ports.venue_service import VenueServicePort
from delivery_hours_service.application.use_cases.get_venue_delivery_hours import (
    GetVenueDeliveryHoursUseCase,
)
from delivery_hours_service.common.config import ServiceConfig, load_config
from delivery_hours_service.infrastructure.adapters.courier_service import (
    CourierServiceAdapter,
)
from delivery_hours_service.infrastructure.adapters.venue_service import (
    VenueServiceAdapter,
)
from delivery_hours_service.infrastructure.clients.http_client import HttpClient


@lru_cache
def get_config() -> ServiceConfig:
    return load_config()


def get_venue_service(
    config: ServiceConfig = Depends(get_config),  # noqa: B008
) -> VenueServicePort:
    http_client = HttpClient(config.venue_service_url)
    return VenueServiceAdapter(config, client=http_client)


def get_courier_service(
    config: ServiceConfig = Depends(get_config),  # noqa: B008
) -> CourierServicePort:
    http_client = HttpClient(config.courier_service_url)
    return CourierServiceAdapter(config, client=http_client)


def get_delivery_hours_use_case(
    venue_service: VenueServicePort = Depends(get_venue_service),  # noqa: B008
    courier_service: CourierServicePort = Depends(get_courier_service),  # noqa: B008
) -> GetVenueDeliveryHoursUseCase:
    return GetVenueDeliveryHoursUseCase(
        venue_service=venue_service,
        courier_service=courier_service,
    )
