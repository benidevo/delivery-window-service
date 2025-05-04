from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from delivery_hours_service.domain.models.delivery_window import WeeklyDeliveryWindow


class ErrorSource(Enum):
    VENUE_SERVICE = "venue_service"
    COURIER_SERVICE = "courier_service"
    DOMAIN_LOGIC = "domain_logic"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ServiceError:
    code: str
    source: ErrorSource
    severity: ErrorSeverity
    details: dict[str, Any] | None = None


@dataclass
class DeliveryHoursResult:
    """
    Contains the result of a delivery hours calculation, including
    the delivery window, any errors encountered, and metadata about the operation.

    This model allows the use case layer to return a response that the
    interface layer can use to determine the appropriate HTTP response.
    """

    delivery_window: WeeklyDeliveryWindow
    errors: list[ServiceError] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls, delivery_window: WeeklyDeliveryWindow, **metadata
    ) -> "DeliveryHoursResult":
        return cls(delivery_window=delivery_window, metadata=metadata)

    @classmethod
    def error(
        cls,
        code: str,
        source: ErrorSource = ErrorSource.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
        delivery_window: WeeklyDeliveryWindow | None = None,
        **metadata,
    ) -> "DeliveryHoursResult":
        window = delivery_window or WeeklyDeliveryWindow.empty()
        error = ServiceError(
            code=code,
            source=source,
            severity=severity,
            details=details,
        )
        return cls(delivery_window=window, errors=[error], metadata=metadata)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_critical_errors(self) -> bool:
        return any(error.severity == ErrorSeverity.ERROR for error in self.errors)

    def add_error(
        self,
        code: str,
        source: ErrorSource = ErrorSource.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.errors.append(
            ServiceError(
                code=code,
                source=source,
                severity=severity,
                details=details,
            )
        )

    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def to_day_schedules(self) -> list[dict]:
        """Convert the delivery window to a list of day schedules for API response."""
        day_schedules = []

        for day, window in self.delivery_window.schedule.items():
            if window.is_closed:
                continue

            times = []
            for time_range in window.windows:
                start_time = f"{time_range.start_time.hours:02d}:{time_range.start_time.minutes:02d}"  # noqa: E501
                end_time = (
                    f"{time_range.end_time.hours:02d}:{time_range.end_time.minutes:02d}"
                )

                times.append(
                    {
                        "start": start_time,
                        "end": end_time,
                    }
                )

            if times:
                day_schedules.append({"day": day.name.lower(), "times": times})

        return day_schedules
