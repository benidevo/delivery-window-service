from fastapi import APIRouter, FastAPI

from delivery_hours_service.common.config import ServiceConfig, load_config


async def get_delivery_hours(city_slug: str, venue_id: str):
    # TODO: please implement this endpoint
    # The base urls for externals services are available in
    # VENUE_SERVICE_URL and COURIER_SERVICE_URL variables

    return {"TODO": f"Please implement me! Got {city_slug=} {venue_id=}"}


class Application:
    def __init__(self, config: ServiceConfig | None = None) -> None:
        self.config = config or load_config()
        self.app = FastAPI(
            title="Delivery Hours Service",
            description="Service for providing delivery hours of venues",
            version="1.0.0",
        )
        self.register_routes()

    def register_routes(self) -> None:
        router = APIRouter(tags=["delivery"])
        router.get("/delivery-hours", response_model=dict)(get_delivery_hours)
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        return self.app
