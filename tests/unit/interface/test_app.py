from fastapi import FastAPI
from fastapi.testclient import TestClient

from delivery_hours_service.common.config import ServiceConfig
from delivery_hours_service.interface.app import Application


def test_should_initialize_with_default_config_when_none_provided() -> None:
    app = Application()

    assert app.config is not None
    assert app.config.venue_service_url.startswith("http://")
    assert app.config.courier_service_url.startswith("http://")


def test_should_use_custom_config_when_provided() -> None:
    custom_config = ServiceConfig(
        venue_service_url="http://test-venue", courier_service_url="http://test-courier"
    )
    app = Application(config=custom_config)

    assert app.config is custom_config
    assert app.config.venue_service_url == "http://test-venue"
    assert app.config.courier_service_url == "http://test-courier"


def test_should_return_fastapi_instance_when_get_app_called() -> None:
    app_instance = Application().get_app()

    assert isinstance(app_instance, FastAPI)


def test_should_register_delivery_hrs_route_when_routes_registered() -> None:
    app_instance = Application().get_app()
    client = TestClient(app_instance)

    response = client.get("/delivery-hours?city_slug=test&venue_id=123")
    assert response.status_code == 200
    assert response.status_code != 404
