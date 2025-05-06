from httpx import AsyncClient, Response
from respx import MockRouter

from delivery_hours_service.common.config import load_config
from delivery_hours_service.main import app

SECONDS_IN_HOUR = 60 * 60
config = load_config()


async def test_simple_venue_delivery_hours(respx_mock: MockRouter) -> None:
    city_slug = "berlin"
    venue_id = "12345"

    # Mock responses of external services
    venue_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 13 * SECONDS_IN_HOUR},
                {"close": 20 * SECONDS_IN_HOUR},
            ]
        },
    )
    venue_url = f"{config.venue_service_url}/venues/{venue_id}/opening-hours"
    respx_mock.get(venue_url).mock(return_value=venue_service_response)
    courier_service_response = Response(
        status_code=200,
        json={
            "monday": [
                {"open": 14 * SECONDS_IN_HOUR},
                {"close": 21 * SECONDS_IN_HOUR},
            ],
            "tuesday": [
                {"open": 10 * SECONDS_IN_HOUR},
                {"close": 23 * SECONDS_IN_HOUR},
            ],
        },
    )
    respx_mock.get(
        f"{config.courier_service_url}/delivery-hours?city={city_slug}"
    ).mock(return_value=courier_service_response)

    # Call our endpoint
    async with AsyncClient(app=app, base_url="http://test") as client:
        url = f"/delivery-hours?city_slug={city_slug}&venue_id={venue_id}"
        response = await client.get(url=url)

    # Assert the response of our endpoint
    assert response.status_code == 200
    assert response.json() == {
        "delivery_hours": {
            # venue service 13-20, courier service 14-21 -> 14-20
            "Monday": "14-20",
            "Tuesday": "Closed",
            "Wednesday": "Closed",
            "Thursday": "Closed",
            "Friday": "Closed",
            "Saturday": "Closed",
            "Sunday": "Closed",
        }
    }
