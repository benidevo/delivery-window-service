import os

from fastapi import FastAPI

app = FastAPI()


VENUE_SERVICE_URL = os.environ.get(
    "VENUE_SERVICE_URL", "http://localhost:8080/venue-service"
)
COURIER_SERVICE_URL = os.environ.get(
    "COURIER_SERVICE_URL", "http://localhost:8080/courier-service"
)


@app.get("/delivery-hours")
async def get_delivery_hours(city_slug: str, venue_id: str):
    # TODO: please implement this endpoint
    # The base urls for externals services are available in
    # VENUE_SERVICE_URL and COURIER_SERVICE_URL variables

    return {"TODO": f"Please implement me! Got {city_slug=} {venue_id=}"}
