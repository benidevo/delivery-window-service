from httpx import AsyncClient, Response
from respx import MockRouter

from delivery_hours_service.common.config import load_config
from delivery_hours_service.main import app

SECONDS_IN_HOUR = 60 * 60
SECONDS_IN_MINUTE = 60
config = load_config()


async def test_should_handle_multiple_delivery_windows_in_day(
    respx_mock: MockRouter,
) -> None:
    city_slug = "berlin"
    venue_id = "multiple_windows"

    venue_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 10 * SECONDS_IN_HOUR},  # 10:00
                {"close": 14 * SECONDS_IN_HOUR},  # 14:00
                {"open": 16 * SECONDS_IN_HOUR},  # 16:00
                {"close": 22 * SECONDS_IN_HOUR},  # 22:00
            ]
        },
    )
    venue_url = f"{config.venue_service_url}/venues/{venue_id}/opening-hours"
    respx_mock.get(venue_url).mock(return_value=venue_service_response)

    courier_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 9 * SECONDS_IN_HOUR},  # 9:00
                {"close": 13 * SECONDS_IN_HOUR},  # 13:00
                {"open": 17 * SECONDS_IN_HOUR},  # 17:00
                {"close": 23 * SECONDS_IN_HOUR},  # 23:00
            ]
        },
    )
    respx_mock.get(
        f"{config.courier_service_url}/delivery-hours?city={city_slug}"
    ).mock(return_value=courier_service_response)

    async with AsyncClient(app=app, base_url="http://test") as client:
        url = f"/delivery-hours?city_slug={city_slug}&venue_id={venue_id}"
        response = await client.get(url=url)

    assert response.status_code == 200
    assert response.json() == {
        "delivery_hours": {
            # Intersections: 10-13 and 17-22
            "Monday": "10-13, 17-22",
            "Tuesday": "Closed",
            "Wednesday": "Closed",
            "Thursday": "Closed",
            "Friday": "Closed",
            "Saturday": "Closed",
            "Sunday": "Closed",
        }
    }


async def test_should_handle_cross_day_delivery_windows(respx_mock: MockRouter) -> None:
    city_slug = "berlin"
    venue_id = "night_venue"

    venue_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 20 * SECONDS_IN_HOUR},  # 20:00
            ],
            "tuesday": [
                {"close": 2 * SECONDS_IN_HOUR},  # 02:00
            ],
        },
    )
    venue_url = f"{config.venue_service_url}/venues/{venue_id}/opening-hours"
    respx_mock.get(venue_url).mock(return_value=venue_service_response)

    courier_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 18 * SECONDS_IN_HOUR},  # 18:00
            ],
            "tuesday": [
                {"close": 1 * SECONDS_IN_HOUR},  # 01:00
                {"open": 10 * SECONDS_IN_HOUR},  # 10:00
                {"close": 22 * SECONDS_IN_HOUR},  # 22:00
            ],
        },
    )
    respx_mock.get(
        f"{config.courier_service_url}/delivery-hours?city={city_slug}"
    ).mock(return_value=courier_service_response)

    async with AsyncClient(app=app, base_url="http://test") as client:
        url = f"/delivery-hours?city_slug={city_slug}&venue_id={venue_id}"
        response = await client.get(url=url)

    assert response.status_code == 200
    assert response.json() == {
        "delivery_hours": {
            # Intersection: Monday 20:00-01:00
            "Monday": "20-1",
            "Tuesday": "Closed",
            "Wednesday": "Closed",
            "Thursday": "Closed",
            "Friday": "Closed",
            "Saturday": "Closed",
            "Sunday": "Closed",
        }
    }


async def test_should_handle_venue_not_found(respx_mock: MockRouter) -> None:
    city_slug = "berlin"
    venue_id = "nonexistent_venue"

    venue_service_response = Response(
        status_code=404, json={"error": "Unknown venue id"}
    )
    venue_url = f"{config.venue_service_url}/venues/{venue_id}/opening-hours"
    respx_mock.get(venue_url).mock(return_value=venue_service_response)

    courier_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 9 * SECONDS_IN_HOUR},  # 9:00
                {"close": 21 * SECONDS_IN_HOUR},  # 21:00
            ]
        },
    )
    respx_mock.get(
        f"{config.courier_service_url}/delivery-hours?city={city_slug}"
    ).mock(return_value=courier_service_response)

    async with AsyncClient(app=app, base_url="http://test") as client:
        url = f"/delivery-hours?city_slug={city_slug}&venue_id={venue_id}"
        response = await client.get(url=url)

    assert response.status_code == 200
    delivery_hours = response.json()["delivery_hours"]

    for day in [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]:
        assert delivery_hours[day] == "Closed"


async def test_should_handle_city_not_found(respx_mock: MockRouter) -> None:
    city_slug = "nonexistent_city"
    venue_id = "12345"

    venue_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 10 * SECONDS_IN_HOUR},  # 10:00
                {"close": 22 * SECONDS_IN_HOUR},  # 22:00
            ]
        },
    )
    venue_url = f"{config.venue_service_url}/venues/{venue_id}/opening-hours"
    respx_mock.get(venue_url).mock(return_value=venue_service_response)

    courier_service_response = Response(status_code=404, json={"error": "Unknown city"})
    respx_mock.get(
        f"{config.courier_service_url}/delivery-hours?city={city_slug}"
    ).mock(return_value=courier_service_response)

    async with AsyncClient(app=app, base_url="http://test") as client:
        url = f"/delivery-hours?city_slug={city_slug}&venue_id={venue_id}"
        response = await client.get(url=url)

    assert response.status_code == 200
    delivery_hours = response.json()["delivery_hours"]

    for day in [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]:
        assert delivery_hours[day] == "Closed"


async def test_should_return_503_on_service_unavailability(
    respx_mock: MockRouter,
) -> None:
    city_slug = "berlin"
    venue_id = "12345"

    venue_service_response = Response(
        status_code=503, json={"error": "Service unavailable"}
    )
    venue_url = f"{config.venue_service_url}/venues/{venue_id}/opening-hours"
    respx_mock.get(venue_url).mock(return_value=venue_service_response)

    courier_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 9 * SECONDS_IN_HOUR},  # 9:00
                {"close": 21 * SECONDS_IN_HOUR},  # 21:00
            ]
        },
    )
    respx_mock.get(
        f"{config.courier_service_url}/delivery-hours?city={city_slug}"
    ).mock(return_value=courier_service_response)

    async with AsyncClient(app=app, base_url="http://test") as client:
        url = f"/delivery-hours?city_slug={city_slug}&venue_id={venue_id}"
        response = await client.get(url=url)

    assert response.status_code == 503
    assert response.json() == {"detail": "Service temporarily unavailable"}
