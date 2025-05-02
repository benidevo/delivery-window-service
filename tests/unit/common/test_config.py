import os
from unittest.mock import patch

from delivery_hours_service.common.config import ServiceConfig, load_config


def test_should_create_service_config_when_initialized_with_values() -> None:
    config = ServiceConfig(
        venue_service_url="http://venue-service",
        courier_service_url="http://courier-service",
    )

    assert config.venue_service_url == "http://venue-service"
    assert config.courier_service_url == "http://courier-service"


def test_should_load_default_values_when_env_variables_not_set() -> None:
    expected_venue_service_url = "http://localhost:8080/venue-service"
    expected_courier_service_url = "http://localhost:8080/courier-service"

    with patch.dict(os.environ, {}, clear=True):
        config = load_config()

        assert config.venue_service_url == expected_venue_service_url
        assert config.courier_service_url == expected_courier_service_url


def test_should_load_from_env_when_env_variables_set() -> None:
    env_vars = {
        "VENUE_SERVICE_URL": "http://custom-venue",
        "COURIER_SERVICE_URL": "http://custom-courier",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = load_config()

        assert config.venue_service_url == "http://custom-venue"
        assert config.courier_service_url == "http://custom-courier"
