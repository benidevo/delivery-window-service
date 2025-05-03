from dataclasses import dataclass, field
from enum import IntEnum

from delivery_hours_service.domain.exceptions.time_exceptions import (
    IncompatibleDaysError,
)
from delivery_hours_service.domain.models.time import TimeRange


class DayOfWeek(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    def to_display_string(self) -> str:
        return self.name.capitalize()


@dataclass(frozen=True)
class DeliveryWindow:
    """
    Represents delivery availability for a single day.
    Contains ordered collection of non-overlapping TimeRanges.
    """

    day: DayOfWeek
    windows: list[TimeRange] = field(default_factory=list)

    def __post_init__(self):
        processed = self._process_windows()
        object.__setattr__(self, "windows", processed)

    def _process_windows(self) -> list[TimeRange]:
        """
        Process a list of delivery time windows by sorting and
        merging overlapping or adjacent windows.

        This method ensures that the resulting list of windows is
        non-overlapping and ordered by start time.
        """
        if not self.windows:
            return []

        sorted_windows = sorted(self.windows, key=lambda w: w.start_time)

        merged = []
        current = sorted_windows[0]

        for i in range(1, len(sorted_windows)):
            next_window = sorted_windows[i]
            merged_window = current.merge(next_window)

            if merged_window:
                current = merged_window
            else:
                merged.append(current)
                current = next_window

        merged.append(current)

        return merged

    @classmethod
    def closed(cls, day: DayOfWeek) -> "DeliveryWindow":
        return cls(day)

    @property
    def is_closed(self) -> bool:
        return len(self.windows) == 0

    def intersect_with(self, other: "DeliveryWindow") -> "DeliveryWindow":
        """
        Calculates the intersection of two delivery windows.
        This method finds the overlapping time periods between
        this delivery window and another delivery window for the same day.
        """
        if self.day != other.day:
            raise IncompatibleDaysError(day1=self.day, day2=other.day)

        if self.is_closed or other.is_closed:
            return DeliveryWindow(self.day, [])

        intersection_windows = []

        for window1 in self.windows:
            for window2 in other.windows:
                intersection = window1.find_intersection(window2)
                if intersection:
                    intersection_windows.append(intersection)

        return DeliveryWindow(self.day, intersection_windows)

    def format(self) -> str:
        """
        Format delivery windows according to business rules.

        e.g.:
        - "10:00-12:00, 14:00-16:00"
        - "Closed"
        """
        if self.is_closed:
            return "Closed"

        formatted_windows = [window.format() for window in self.windows]
        return ", ".join(formatted_windows)

    def __repr__(self) -> str:
        return f"DeliveryWindow({self.day.name}, {self.windows})"


@dataclass(frozen=True)
class WeeklyDeliveryWindow:
    """
    Represents a weekly schedule of delivery windows for each day of the week.

    This class manages delivery windows for all days of the week, providing methods
    to create, manipulate, and format delivery schedules. Any day not explicitly
    provided will default to a closed delivery window.
    """

    schedule: dict[DayOfWeek, DeliveryWindow] = field(default_factory=dict)

    def __post_init__(self):
        complete_schedule = {}
        for day in DayOfWeek:
            complete_schedule[day] = self.schedule.get(day, DeliveryWindow.closed(day))

        object.__setattr__(self, "schedule", complete_schedule)

    @classmethod
    def empty(cls) -> "WeeklyDeliveryWindow":
        return cls({})

    def get_day_window(self, day: DayOfWeek) -> DeliveryWindow:
        return self.schedule[day]

    def intersect_with(self, other: "WeeklyDeliveryWindow") -> "WeeklyDeliveryWindow":
        intersection_days = {}

        for day in DayOfWeek:
            our_day = self.schedule[day]
            other_day = other.schedule[day]
            intersection_days[day] = our_day.intersect_with(other_day)

        return WeeklyDeliveryWindow(intersection_days)

    def to_api_format(self) -> dict[str, str]:
        result = {}

        for day in DayOfWeek:
            day_window = self.schedule[day]
            result[day.to_display_string()] = day_window.format()

        return result

    def __repr__(self) -> str:
        return f"WeeklyDeliveryWindow({self.schedule})"
