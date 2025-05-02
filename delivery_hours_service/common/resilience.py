from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps

from delivery_hours_service.common.logging import StructuredLogger

logger = StructuredLogger(__name__)


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    reset_timeout: timedelta = timedelta(seconds=60)
    half_open_max_calls: int = 3


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failures: int = 0
        self.last_failure: datetime | None = None
        self.state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self.half_open_calls: int = 0

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure = datetime.now(UTC)

        if self.failures >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                failures=self.failures,
                threshold=self.config.failure_threshold,
            )

    def record_success(self) -> None:
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failures = 0
                logger.info(
                    "circuit_breaker_closed", half_open_successes=self.half_open_calls
                )

    def can_execute(self) -> bool:
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            if (
                self.last_failure
                and datetime.now(UTC) - self.last_failure > self.config.reset_timeout
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("circuit_breaker_half_open")
                return True
            return False

        return True


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""

    pass


def circuit_breaker(config: CircuitBreakerConfig):
    """
    A decorator function that implements the Circuit Breaker pattern for resilience.

    The circuit breaker prevents a function from being called repeatedly when
    it is failing, which can help prevent cascading failures.
    It tracks failures and will "open" the circuit when the failure threshold
    is reached, preventing further calls.
    """
    breaker = CircuitBreaker(config)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not breaker.can_execute():
                raise CircuitBreakerError("Circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise e

        return wrapper

    return decorator
