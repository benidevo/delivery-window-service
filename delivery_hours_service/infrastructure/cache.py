import hashlib
import json

import redis.asyncio as redis

from delivery_hours_service.common.config import ServiceConfig
from delivery_hours_service.common.logging import StructuredLogger

logger = StructuredLogger(__name__)


class CacheService:
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self.config.redis_url,
                    decode_responses=True,
                    health_check_interval=30,
                )
                # Test connection
                await self._client.ping()
                logger.info(
                    "Redis connection established", redis_url=self.config.redis_url
                )
            except Exception as e:
                logger.warning(
                    "Failed to connect to Redis, caching disabled",
                    error=str(e),
                    redis_url=self.config.redis_url,
                )
                self._client = None
                raise
        return self._client

    def _generate_cache_key(self, service: str, endpoint: str, params: dict) -> str:
        sorted_params = json.dumps(params, sort_keys=True) if params else ""
        key_data = f"{service}:{endpoint}:{sorted_params}"

        # Use hash to keep keys reasonably short
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"delivery_service:{service}:{key_hash}"

    async def get(
        self, service: str, endpoint: str, params: dict | None = None
    ) -> dict | None:
        try:
            client = await self._get_client()
            cache_key = self._generate_cache_key(service, endpoint, params or {})

            cached_data = await client.get(cache_key)
            if cached_data:
                logger.debug(
                    "Cache hit", service=service, endpoint=endpoint, cache_key=cache_key
                )
                return json.loads(cached_data)

            logger.debug(
                "Cache miss", service=service, endpoint=endpoint, cache_key=cache_key
            )
            return None

        except Exception as e:
            logger.warning(
                "Cache get failed", error=str(e), service=service, endpoint=endpoint
            )
            return None

    async def set(
        self,
        service: str,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
    ) -> bool:
        try:
            client = await self._get_client()
            cache_key = self._generate_cache_key(service, endpoint, params or {})

            await client.setex(
                cache_key, self.config.cache_ttl_seconds, json.dumps(data)
            )

            logger.debug(
                "Cache set successful",
                service=service,
                endpoint=endpoint,
                cache_key=cache_key,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
            return True

        except Exception as e:
            logger.warning(
                "Cache set failed", error=str(e), service=service, endpoint=endpoint
            )
            return False

    async def invalidate_service(self, service: str) -> int:
        try:
            client = await self._get_client()
            pattern = f"delivery_service:{service}:*"

            keys = await client.keys(pattern)
            if keys:
                deleted_count = await client.delete(*keys)
                logger.info(
                    "Cache invalidation completed",
                    service=service,
                    deleted_keys=deleted_count,
                )
                return deleted_count
            return 0

        except Exception as e:
            logger.warning("Cache invalidation failed", error=str(e), service=service)
            return 0

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis connection closed")


# Global cache instance (will be initialized in application startup)
cache_service: CacheService | None = None


def get_cache_service() -> CacheService | None:
    """Get the global cache service instance."""
    return cache_service


def initialize_cache_service(config: ServiceConfig):
    """Initialize the global cache service."""
    global cache_service
    cache_service = CacheService(config)
