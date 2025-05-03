from dataclasses import dataclass, field
from functools import total_ordering

from delivery_hours_service.domain.exceptions.time_exceptions import (
    InvalidDurationError,
    InvalidTimeError,
)

MAX_HOURS = 23
MAX_MINUTES = 59
MIN_HOURS = 0
MIN_MINUTES = 0
MINUTES_IN_DAY = 1440
SECONDS_IN_DAY = 86400
MINIMUM_DURATION_MINUTES = 30


@dataclass(frozen=True)
@total_ordering
class Time:
    """
    Represents an immutable time of day using hours and minutes.

    This class handles time values with proper validations, supports various
    conversion methods, and implements time arithmetic operations.
    """

    hours: int
    minutes: int
    _minutes_since_midnight: int = field(init=False)

    def __post_init__(self):
        if not (MIN_HOURS <= self.hours <= MAX_HOURS):
            raise InvalidTimeError(
                hours=self.hours,
                message=f"Hours must be between {MIN_HOURS} and {MAX_HOURS}",
            )
        if not (MIN_MINUTES <= self.minutes <= MAX_MINUTES):
            raise InvalidTimeError(
                minutes=self.minutes,
                message=f"Minutes must be between {MIN_MINUTES} and {MAX_MINUTES}",
            )

        object.__setattr__(
            self, "_minutes_since_midnight", self.hours * 60 + self.minutes
        )

    @classmethod
    def from_minutes(cls, minutes_since_midnight: int) -> "Time":
        if not (MIN_MINUTES <= minutes_since_midnight < MINUTES_IN_DAY):
            message = (
                f"Minutes since midnight must be between 0 and {MINUTES_IN_DAY - 1}"
            )
            raise InvalidTimeError(message=message)

        hours = minutes_since_midnight // 60
        minutes = minutes_since_midnight % 60
        return cls(hours, minutes)

    @classmethod
    def from_unix_seconds(cls, unix_seconds: int) -> "Time":
        if not (0 <= unix_seconds < SECONDS_IN_DAY):
            raise InvalidTimeError(
                message=f"Unix seconds must be between 0 and {SECONDS_IN_DAY - 1}"
            )

        minutes_since_midnight = unix_seconds // 60
        return cls.from_minutes(minutes_since_midnight)

    @property
    def minutes_since_midnight(self) -> int:
        return self._minutes_since_midnight

    def add_minutes(self, minutes: int) -> "Time":
        new_minutes_since_midnight = (
            self._minutes_since_midnight + minutes
        ) % MINUTES_IN_DAY
        return self.from_minutes(new_minutes_since_midnight)

    def subtract_minutes(self, minutes: int) -> "Time":
        return self.add_minutes(-minutes)

    def format(self) -> str:
        """
        Format time according to business rules.
        - HH:MM format with HH always two digits
        - Omit :00 when minutes are zero

        e.g. 14:00 -> 14, 14:30 -> 14:30
        """
        if self.minutes == 0:
            return f"{self.hours:02d}"
        return f"{self.hours:02d}:{self.minutes:02d}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Time):
            return False
        return self._minutes_since_midnight == other._minutes_since_midnight

    def __lt__(self, other: "Time") -> bool:
        return self._minutes_since_midnight < other._minutes_since_midnight

    def __repr__(self) -> str:
        return f"Time({self.hours:02d}:{self.minutes:02d})"

    def __str__(self) -> str:
        return self.format()


@dataclass(frozen=True)
class TimeRange:
    """
    Represents a time range with a start and end time.

    This class handles both regular time ranges and overnight ranges
    (crossing midnight). A `TimeRange` with equal `start_time` and `end_time`
    is treated as an overnight range, representing a full day. This ensures
    consistent handling of edge cases and simplifies operations like merging
    and intersection. It provides functionality to check for overlap, adjacency,
    and to perform operations like merging
    and finding intersections between time ranges.
    """

    start_time: Time
    end_time: Time
    _is_overnight: bool = field(init=False, default=False)
    _duration_minutes: int = field(init=False)

    def __post_init__(self):
        is_overnight = (
            self.start_time > self.end_time or self.start_time == self.end_time
        )
        object.__setattr__(self, "_is_overnight", is_overnight)

        duration = self._calculate_duration()
        object.__setattr__(self, "_duration_minutes", duration)

        if self._duration_minutes < MINIMUM_DURATION_MINUTES:
            raise InvalidDurationError(
                duration_minutes=self._duration_minutes,
                minimum_duration=MINIMUM_DURATION_MINUTES,
            )

    def _calculate_duration(self) -> int:
        if self._is_overnight:
            return (
                MINUTES_IN_DAY - self.start_time.minutes_since_midnight
            ) + self.end_time.minutes_since_midnight
        return (
            self.end_time.minutes_since_midnight
            - self.start_time.minutes_since_midnight
        )

    @property
    def duration_minutes(self) -> int:
        return self._duration_minutes

    @property
    def is_overnight(self) -> bool:
        return self._is_overnight

    def contains_time(self, time: Time) -> bool:
        if self.is_overnight:
            return time >= self.start_time or time <= self.end_time

        return self.start_time <= time <= self.end_time

    def overlaps_with(self, other: "TimeRange") -> bool:
        if (
            self.contains_time(other.start_time)
            or self.contains_time(other.end_time)
            or other.contains_time(self.start_time)
            or other.contains_time(self.end_time)
        ):
            return True

        # Special case: both are overnight ranges and cover the full day
        if self.is_overnight and other.is_overnight:
            return True

        return False

    def is_adjacent_to(self, other: "TimeRange") -> bool:
        if not self.is_overnight and not other.is_overnight:
            return (
                self.start_time == other.end_time or self.end_time == other.start_time
            )

        return False

    def merge(self, other: "TimeRange") -> "TimeRange | None":
        """
        Merge two time ranges if they overlap or are adjacent.

        Merging logic:
        - If ranges overlap or are adjacent, they are merged.
        - For overnight ranges, the one with greater coverage is returned.
        - For regular ranges, the merged range spans from
            the earliest start_time to the latest end_time.
        """
        if not (self.overlaps_with(other) or self.is_adjacent_to(other)):
            return None

        if self.is_overnight or other.is_overnight:
            if (self.is_overnight and not other.is_overnight) or (
                self.is_overnight
                and other.is_overnight
                and self.duration_minutes >= other.duration_minutes
            ):
                return TimeRange(self.start_time, self.end_time)
            else:
                return TimeRange(other.start_time, other.end_time)

        return TimeRange(
            min(self.start_time, other.start_time), max(self.end_time, other.end_time)
        )

    def find_intersection(self, other: "TimeRange") -> "TimeRange | None":
        """
        Find the intersection between this TimeRange and another TimeRange.

        Handles special cases:
        - If time ranges don't overlap, returns None
        - If both time ranges are overnight, returns the smaller range
        - If one time range is overnight, checks if the other is fully contained
        - For regular time ranges, returns the overlapping portion
        """
        if not self.overlaps_with(other):
            return None

        if self.is_overnight and other.is_overnight:
            return TimeRange(
                self.start_time
                if self.duration_minutes <= other.duration_minutes
                else other.start_time,
                self.end_time
                if self.duration_minutes <= other.duration_minutes
                else other.end_time,
            )

        elif self.is_overnight:
            return (
                TimeRange(other.start_time, other.end_time)
                if self.contains_time(other.start_time)
                and self.contains_time(other.end_time)
                else None
            )
        elif other.is_overnight:
            return (
                TimeRange(self.start_time, self.end_time)
                if other.contains_time(self.start_time)
                and other.contains_time(self.end_time)
                else None
            )

        start = max(self.start_time, other.start_time)
        end = min(self.end_time, other.end_time)

        try:
            return TimeRange(start, end)
        except InvalidDurationError:
            return None

    def format(self) -> str:
        """
        Format time range according to business rules.

        The formatted string is represented like "14-20" or "13:30-15"
        """
        return f"{self.start_time.format()}-{self.end_time.format()}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeRange):
            return False
        return self.start_time == other.start_time and self.end_time == other.end_time

    def __repr__(self) -> str:
        return f"TimeRange({self.start_time} - {self.end_time})"

    def __str__(self) -> str:
        return self.format()
