import os
from dataclasses import dataclass


@dataclass
class ServiceConfig:
    venue_service_url: str
    courier_service_url: str


def load_config() -> ServiceConfig:
    return ServiceConfig(
        venue_service_url=os.environ.get(
            "VENUE_SERVICE_URL", "http://localhost:8080/venue-service"
        ),
        courier_service_url=os.environ.get(
            "COURIER_SERVICE_URL", "http://localhost:8080/courier-service"
        ),
    )
