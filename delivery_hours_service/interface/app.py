from fastapi import FastAPI

from delivery_hours_service.common.config import ServiceConfig, load_config
from delivery_hours_service.common.middleware import (
    correlation_id_middleware,
    error_handling_middleware,
)
from delivery_hours_service.infrastructure.cache import initialize_cache_service
from delivery_hours_service.infrastructure.clients.http_client import (
    lifespan_http_clients,
)
from delivery_hours_service.interface.api.delivery_hours_api import (
    router as delivery_router,
)
from delivery_hours_service.interface.api.health import (
    router as health_router,
)


class Application:
    def __init__(self, config: ServiceConfig | None = None) -> None:
        self.config = config or load_config()
        self.app = FastAPI(
            title="Delivery Window Service",
            description="Service for calculating delivery windows based on venue opening hours and courier availability",  # noqa: E501
            version="1.0.0",
            lifespan=lifespan_http_clients,
            redirect_slashes=False,
        )
        self.initialize_services()
        self.register_middleware()
        self.register_routes()

    def initialize_services(self) -> None:
        initialize_cache_service(self.config)

    def register_middleware(self) -> None:
        # Order matters: correlation_id_middleware must come before
        # error_handling_middleware
        # so that correlation IDs are available in error logs
        self.app.middleware("http")(correlation_id_middleware)
        self.app.middleware("http")(error_handling_middleware)

    def register_routes(self) -> None:
        self.app.include_router(delivery_router)
        self.app.include_router(health_router)

    def get_app(self) -> FastAPI:
        return self.app
