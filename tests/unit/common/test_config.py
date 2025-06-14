import os
from unittest.mock import patch

from delivery_hours_service.common.config import ServiceConfig, load_config


def test_should_create_service_config_when_initialized_with_values() -> None:
    config = ServiceConfig(
        venue_service_url="http://venue-service",
        courier_service_url="http://courier-service",
        redis_url="redis://localhost:6379",
        cache_ttl_seconds=300,
    )

    assert config.venue_service_url == "http://venue-service"
    assert config.courier_service_url == "http://courier-service"
    assert config.redis_url == "redis://localhost:6379"
    assert config.cache_ttl_seconds == 300


def test_should_load_default_values_when_env_variables_not_set() -> None:
    expected_venue_service_url = "http://localhost:8080/venue-service"
    expected_courier_service_url = "http://localhost:8080/courier-service"
    expected_redis_url = "redis://localhost:6379"
    expected_cache_ttl = 300

    with patch.dict(os.environ, {}, clear=True):
        config = load_config()

        assert config.venue_service_url == expected_venue_service_url
        assert config.courier_service_url == expected_courier_service_url
        assert config.redis_url == expected_redis_url
        assert config.cache_ttl_seconds == expected_cache_ttl


def test_should_load_from_env_when_env_variables_set() -> None:
    env_vars = {
        "VENUE_SERVICE_URL": "http://custom-venue",
        "COURIER_SERVICE_URL": "http://custom-courier",
        "REDIS_URL": "redis://custom-redis:6379",
        "CACHE_TTL_SECONDS": "600",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = load_config()

        assert config.venue_service_url == "http://custom-venue"
        assert config.courier_service_url == "http://custom-courier"
        assert config.redis_url == "redis://custom-redis:6379"
        assert config.cache_ttl_seconds == 600
