from delivery_hours_service.domain.exceptions.base import DomainError


class TimeError(DomainError):
    """Base class for all time-related exceptions."""

    pass


class InvalidTimeError(TimeError):
    """Raised when a time value is outside the allowed range."""

    def __init__(
        self,
        hours: int | None = None,
        minutes: int | None = None,
        message: str | None = None,
    ):
        if message:
            self.message = message
        elif hours is not None and minutes is not None:
            self.message = (
                f"Invalid time: {hours:02d}:{minutes:02d}. "
                + "Hours must be 0-23 and minutes 0-59."
            )
        elif hours is not None:
            self.message = f"Invalid hours: {hours}. Hours must be between 0 and 23."
        elif minutes is not None:
            self.message = (
                f"Invalid minutes: {minutes}. Minutes must be between 0 and 59."
            )
        else:
            self.message = "Invalid time value."
        super().__init__(self.message)


class InvalidDurationError(TimeError):
    """Raised when a time range has a duration less than the minimum allowed."""

    def __init__(self, duration_minutes: int, minimum_duration: int):
        self.duration_minutes = duration_minutes
        self.minimum_duration = minimum_duration
        self.message = (
            f"Duration must be at least {minimum_duration} minutes, "
            f"but got {duration_minutes} minutes."
        )
        super().__init__(self.message)


class TimeRangeError(DomainError):
    """Base class for all time range-related exceptions."""

    pass


class InvalidTimeRangeError(TimeRangeError):
    """Raised when a time range is invalid (e.g., invalid start/end combination)."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class DeliveryWindowError(DomainError):
    """Base class for all delivery window-related exceptions."""

    pass


class IncompatibleDaysError(DeliveryWindowError):
    """
    Raised when trying to perform operations on delivery windows
    from different days.
    """

    def __init__(self, day1, day2):
        self.day1 = day1
        self.day2 = day2
        self.message = f"Cannot intersect different days: {day1} vs {day2}"
        super().__init__(self.message)
