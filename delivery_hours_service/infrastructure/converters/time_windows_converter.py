from functools import lru_cache

from delivery_hours_service.common.logging import StructuredLogger
from delivery_hours_service.domain.models.delivery_window import (
    DayOfWeek,
    DeliveryWindow,
    WeeklyDeliveryWindow,
)
from delivery_hours_service.domain.models.time import Time, TimeRange

logger = StructuredLogger(__name__)


class TimeWindowsConverter:
    """
    A Converter that transforms external API time windows format to domain models.

    It is used by both VenueService and CourierService adapters since they share the
    same response payload format.
    """

    @staticmethod
    def convert_to_weekly_delivery_window(
        data: dict[str, list[dict[str, int]]],
    ) -> WeeklyDeliveryWindow:
        """
        Converts the external API response format to the domain model.

        The format expected is:
        {
          "monday": [
            { "open": 28800 },
            { "close": 72000 }
          ],
          ...
        }

        Where times are represented in UNIX seconds since midnight.
        """
        schedule = TimeWindowsConverter.handle_all_days(data)
        return WeeklyDeliveryWindow(schedule)

    @staticmethod
    def handle_all_days(
        data: dict[str, list[dict[str, int]]],
    ) -> dict[DayOfWeek, DeliveryWindow]:
        """
        Converts raw delivery hours data into structured DeliveryWindow objects
        for each day of the week.
        Processes both regular time windows and overnight (cross-day) windows.

        For overnight windows, it identifies when a day has an opening time
        without a closing time, and links it with the
        following day's closing time.
        """
        day_mapping = TimeWindowsConverter.get_day_mapping()
        day_enums = list(DayOfWeek)
        day_name_map = TimeWindowsConverter.get_day_name_mapping()
        schedule = {day: DeliveryWindow.closed(day) for day in day_enums}

        for day_name, time_windows in data.items():
            day_enum = day_mapping.get(day_name.lower())
            if day_enum is None:
                logger.warning(f"Unknown day name: {day_name}")
                continue

            windows = TimeWindowsConverter.process_day_windows(time_windows)

            if windows:
                schedule[day_enum] = DeliveryWindow(day_enum, windows)

        for i, day_enum in enumerate(day_enums):
            next_day_enum = day_enums[(i + 1) % len(day_enums)]
            day_name = day_name_map[day_enum].lower()
            next_day_name = day_name_map[next_day_enum].lower()

            if day_name not in data or next_day_name not in data:
                continue

            current_day_opens = []
            next_day_closes = []

            for window in data.get(day_name, []):
                if "open" in window:
                    current_day_opens.append(window["open"])

            for window in data.get(next_day_name, []):
                if "close" in window:
                    next_day_closes.append(window["close"])

            if not current_day_opens or not next_day_closes:
                continue

            current_day_opens.sort()
            next_day_closes.sort()

            regular_opens_count = 0
            regular_closes_count = 0

            for window in data.get(day_name, []):
                if "open" in window:
                    regular_opens_count += 1
                elif "close" in window:
                    regular_closes_count += 1

            if current_day_opens and next_day_closes:
                # Take the latest open time and the earliest close time
                open_time = current_day_opens[-1]

                try:
                    # Create an overnight window
                    start_time = Time.from_unix_seconds(open_time)
                    end_time = Time.from_unix_seconds(0)  # Midnight

                    # Create an overnight window
                    time_range = TimeRange(start_time, end_time)

                    # Add to the current day's windows
                    existing_windows = schedule[day_enum].windows
                    new_windows = list(existing_windows) + [time_range]
                    schedule[day_enum] = DeliveryWindow(day_enum, new_windows)

                except Exception as e:
                    logger.warning(
                        f"Invalid overnight time range: {open_time}-0: {str(e)}"
                    )

        return schedule

    @staticmethod
    def process_day_windows(time_windows: list[dict[str, int]]) -> list[TimeRange]:
        """
        Processes raw time windows for a single day into domain TimeRange objects.

        The method handles potentially inconsistent data by:
        1. Separating open and close times into separate lists
        2. Sorting both lists chronologically
        3. Pairing each open time with the next available close time that comes after it
        4. Skipping invalid pairs or times that can't be converted

        Expected input format:
        [{"open": 28800}, {"close": 72000}, {"open": 75600}, {"close": 86399}, ...]

        Where values are UNIX seconds since midnight (0-86399):
        - 28800 = 8:00 AM (28800 seconds after midnight)
        - 72000 = 8:00 PM (72000 seconds after midnight)
        """
        if len(time_windows) % 2 != 0:
            logger.warning(f"Odd number of time entries: {time_windows}")

        time_ranges = []
        opens = []
        closes = []

        for window in time_windows:
            if "open" in window:
                opens.append(window["open"])
            elif "close" in window:
                closes.append(window["close"])

        if len(opens) != len(closes):
            logger.warning(
                f"Mismatch between opening and closing times: {len(opens)} "
                f"openings and {len(closes)} closings"
            )

        # Create proper pairs that match each open with the next available close
        # This handles cases where there are orphaned opens or closes
        paired_windows = []

        opens.sort()
        closes.sort()

        for open_time in opens:
            # Find the next close time that is after this open time
            for i, close_time in enumerate(closes):
                if close_time > open_time:
                    paired_windows.append((open_time, close_time))
                    # Remove this close time so it doesn't get used again
                    closes.pop(i)
                    break

        for open_time, close_time in paired_windows:
            try:
                start_time = Time.from_unix_seconds(open_time)
                end_time = Time.from_unix_seconds(close_time)

                time_range = TimeRange(start_time, end_time)
                time_ranges.append(time_range)
            except Exception as e:
                logger.warning(
                    f"Invalid time range: {open_time}-{close_time}: {str(e)}"
                )
                continue

        return time_ranges

    @staticmethod
    @lru_cache(maxsize=1)
    def get_day_mapping() -> dict[str, DayOfWeek]:
        return {
            DayOfWeek.MONDAY.name.lower(): DayOfWeek.MONDAY,
            DayOfWeek.TUESDAY.name.lower(): DayOfWeek.TUESDAY,
            DayOfWeek.WEDNESDAY.name.lower(): DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY.name.lower(): DayOfWeek.THURSDAY,
            DayOfWeek.FRIDAY.name.lower(): DayOfWeek.FRIDAY,
            DayOfWeek.SATURDAY.name.lower(): DayOfWeek.SATURDAY,
            DayOfWeek.SUNDAY.name.lower(): DayOfWeek.SUNDAY,
        }

    @staticmethod
    @lru_cache(maxsize=1)
    def get_day_name_mapping() -> dict[DayOfWeek, str]:
        return {
            DayOfWeek.MONDAY: "monday",
            DayOfWeek.TUESDAY: "tuesday",
            DayOfWeek.WEDNESDAY: "wednesday",
            DayOfWeek.THURSDAY: "thursday",
            DayOfWeek.FRIDAY: "friday",
            DayOfWeek.SATURDAY: "saturday",
            DayOfWeek.SUNDAY: "sunday",
        }
