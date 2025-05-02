import pytest
from httpx import AsyncClient, Response
from respx import MockRouter

from delivery_hours_service.main import COURIER_SERVICE_URL, VENUE_SERVICE_URL, app

SECONDS_IN_HOUR = 60 * 60


# TODO: Get rid of pytest.mark.xfail after implementing GET /delivery-hours
@pytest.mark.xfail
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
    respx_mock.get(f"{VENUE_SERVICE_URL}/venues/{venue_id}/opening-hours").mock(
        return_value=venue_service_response
    )
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
    respx_mock.get(f"{COURIER_SERVICE_URL}/delivery-hours?city={city_slug}").mock(
        return_value=courier_service_response
    )

    # Call our endpoint
    async with AsyncClient(app=app, base_url="http://test") as client:
        url = f"/delivery-hours?city_slug={city_slug}&venue_id={venue_id}"
        response = await client.get(url=url)

    # Assert the response of our endpoint
    assert response.status_code == 200
    assert response.json() == {
        "delivery_hours": {
            "Monday": "14-20",  # venue service 13-20, courier service 14-21 -> 14-20
            "Tuesday": "Closed",
            "Wednesday": "Closed",
            "Thursday": "Closed",
            "Friday": "Closed",
            "Saturday": "Closed",
            "Sunday": "Closed",
        }
    }
