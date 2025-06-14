import os
from dataclasses import dataclass


@dataclass
class ServiceConfig:
    venue_service_url: str
    courier_service_url: str
    redis_url: str
    cache_ttl_seconds: int


def load_config() -> ServiceConfig:
    return ServiceConfig(
        venue_service_url=os.environ.get(
            "VENUE_SERVICE_URL", "http://localhost:8080/venue-service"
        ),
        courier_service_url=os.environ.get(
            "COURIER_SERVICE_URL", "http://localhost:8080/courier-service"
        ),
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379"),
        cache_ttl_seconds=int(
            os.environ.get("CACHE_TTL_SECONDS", "300")
        ),  # 5 minutes default
    )
