from fastapi import FastAPI
from fastapi.routing import APIRoute

from delivery_hours_service.common.config import ServiceConfig
from delivery_hours_service.interface.app import Application


def test_should_initialize_with_default_config_when_none_provided() -> None:
    app = Application()

    assert app.config is not None
    assert app.config.venue_service_url.startswith("http://")
    assert app.config.courier_service_url.startswith("http://")


def test_should_use_custom_config_when_provided() -> None:
    custom_config = ServiceConfig(
        venue_service_url="http://test-venue",
        courier_service_url="http://test-courier",
        redis_url="redis://localhost:6379",
        cache_ttl_seconds=300,
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
    routes = app_instance.routes
    delivery_routes = [
        route
        for route in routes
        if isinstance(route, APIRoute) and "delivery-hours" in route.path
    ]

    assert len(delivery_routes) > 0

    delivery_get_route = next(
        (route for route in delivery_routes if "GET" in route.methods), None
    )
    assert delivery_get_route is not None

    expected_params = {"city_slug", "venue_id"}
    route_params = {param.name for param in delivery_get_route.dependant.query_params}
    assert expected_params.issubset(route_params)
