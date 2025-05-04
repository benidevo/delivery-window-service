from fastapi import FastAPI

from delivery_hours_service.common.config import ServiceConfig, load_config
from delivery_hours_service.infrastructure.clients.http_client import (
    lifespan_http_clients,
)
from delivery_hours_service.interface.api.delivery_hours_api import (
    router as delivery_router,
)


class Application:
    def __init__(self, config: ServiceConfig | None = None) -> None:
        self.config = config or load_config()
        self.app = FastAPI(
            title="Delivery Hours Service",
            description="Service for providing delivery hours of venues",
            version="1.0.0",
            lifespan=lifespan_http_clients,
        )
        self.register_routes()

    def register_routes(self) -> None:
        self.app.include_router(delivery_router)

    def get_app(self) -> FastAPI:
        return self.app
