from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from delivery_hours_service.common.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerState,
    circuit_breaker,
)


def test_circuit_breaker_config_should_initialize_with_default_values() -> None:
    config = CircuitBreakerConfig()

    assert config.failure_threshold == 5
    assert config.reset_timeout == timedelta(seconds=60)
    assert config.half_open_max_calls == 3


def test_circuit_breaker_config_should_initialize_with_custom_values() -> None:
    config = CircuitBreakerConfig(
        failure_threshold=10,
        reset_timeout=timedelta(seconds=120),
        half_open_max_calls=5,
    )

    assert config.failure_threshold == 10
    assert config.reset_timeout == timedelta(seconds=120)
    assert config.half_open_max_calls == 5


@pytest.fixture
def configured_circuit_breaker() -> CircuitBreaker:
    return CircuitBreaker(
        CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout=timedelta(seconds=30),
            half_open_max_calls=2,
        )
    )


def test_circuit_breaker_should_initialize_in_closed_state(
    configured_circuit_breaker: CircuitBreaker,
) -> None:
    assert configured_circuit_breaker.state == CircuitBreakerState.CLOSED
    assert configured_circuit_breaker.failures == 0
    assert configured_circuit_breaker.last_failure is None
    assert configured_circuit_breaker.half_open_calls == 0


def test_circuit_breaker_should_record_failure_and_increment_counter(
    configured_circuit_breaker: CircuitBreaker,
) -> None:
    assert configured_circuit_breaker.failures == 0

    configured_circuit_breaker.record_failure()

    assert configured_circuit_breaker.failures == 1
    assert configured_circuit_breaker.last_failure is not None
    assert configured_circuit_breaker.state == CircuitBreakerState.CLOSED


def test_circuit_breaker_should_open_circuit_when_failure_threshold_reached(
    configured_circuit_breaker: CircuitBreaker,
) -> None:
    for _ in range(3):
        configured_circuit_breaker.record_failure()

    assert configured_circuit_breaker.failures == 3
    assert configured_circuit_breaker.state == CircuitBreakerState.OPEN


def test_circuit_breaker_should_always_allow_execution_when_closed(
    configured_circuit_breaker: CircuitBreaker,
) -> None:
    assert configured_circuit_breaker.can_execute() is True


def test_circuit_breaker_should_deny_execution_when_open_and_timeout_not_reached(
    configured_circuit_breaker: CircuitBreaker,
) -> None:
    for _ in range(3):
        configured_circuit_breaker.record_failure()

    assert configured_circuit_breaker.can_execute() is False


def test_circuit_breaker_should_transition_to_half_open_when_timeout_reached(
    configured_circuit_breaker: CircuitBreaker,
) -> None:
    for _ in range(3):
        configured_circuit_breaker.record_failure()

    # Simulate time passing beyond reset_timeout
    configured_circuit_breaker.last_failure = datetime.now(UTC) - timedelta(seconds=31)

    assert configured_circuit_breaker.can_execute() is True
    assert configured_circuit_breaker.state == CircuitBreakerState.HALF_OPEN
    assert configured_circuit_breaker.half_open_calls == 0


def test_circuit_breaker_should_track_successful_calls_in_half_open_state(
    configured_circuit_breaker: CircuitBreaker,
) -> None:
    configured_circuit_breaker.state = CircuitBreakerState.HALF_OPEN

    configured_circuit_breaker.record_success()

    assert configured_circuit_breaker.half_open_calls == 1
    assert configured_circuit_breaker.state == CircuitBreakerState.HALF_OPEN


def test_circuit_breaker_should_close_circuit_after_sufficient_half_open_successes(
    configured_circuit_breaker: CircuitBreaker,
) -> None:
    configured_circuit_breaker.state = CircuitBreakerState.HALF_OPEN
    configured_circuit_breaker.failures = 3

    configured_circuit_breaker.record_success()
    configured_circuit_breaker.record_success()

    assert configured_circuit_breaker.state == CircuitBreakerState.CLOSED
    assert configured_circuit_breaker.failures == 0


@pytest.fixture
def circuit_breaker_test_config() -> CircuitBreakerConfig:
    return CircuitBreakerConfig(
        failure_threshold=2,
        reset_timeout=timedelta(seconds=30),
        half_open_max_calls=2,
    )


@pytest.mark.asyncio
async def test_circuit_breaker_decorator_should_call_wrapped_function_when_circuit_closed(  # noqa: E501
    circuit_breaker_test_config: CircuitBreakerConfig,
) -> None:
    mock_func = AsyncMock(return_value="success")
    decorated_func = circuit_breaker(circuit_breaker_test_config)(mock_func)

    result = await decorated_func("arg1", kwarg1="value1")

    assert result == "success"
    mock_func.assert_called_once_with("arg1", kwarg1="value1")


@pytest.mark.asyncio
async def test_circuit_breaker_decorator_should_record_success_after_successful_call(
    circuit_breaker_test_config: CircuitBreakerConfig,
) -> None:
    mock_func = AsyncMock(return_value="success")

    with patch(
        "delivery_hours_service.common.resilience.CircuitBreaker.record_success"
    ) as mock_record_success:
        decorated_func = circuit_breaker(circuit_breaker_test_config)(mock_func)
        await decorated_func()

        mock_record_success.assert_called_once()


@pytest.mark.asyncio
async def test_circuit_breaker_decorator_should_record_failure_when_wrapped_function_raises_exception(  # noqa: E501
    circuit_breaker_test_config: CircuitBreakerConfig,
) -> None:
    mock_func = AsyncMock(side_effect=ValueError("Test error"))

    with patch(
        "delivery_hours_service.common.resilience.CircuitBreaker.record_failure"
    ) as mock_record_failure:
        decorated_func = circuit_breaker(circuit_breaker_test_config)(mock_func)

        with pytest.raises(ValueError, match="Test error"):
            await decorated_func()

        mock_record_failure.assert_called_once()


@pytest.mark.asyncio
async def test_circuit_breaker_decorator_should_raise_circuit_breaker_error_when_open(
    circuit_breaker_test_config: CircuitBreakerConfig,
) -> None:
    mock_func = AsyncMock(return_value="success")

    with patch(
        "delivery_hours_service.common.resilience.CircuitBreaker.can_execute",
        return_value=False,
    ):
        decorated_func = circuit_breaker(circuit_breaker_test_config)(mock_func)

        with pytest.raises(CircuitBreakerError, match="Circuit breaker is open"):
            await decorated_func()

        mock_func.assert_not_called()
