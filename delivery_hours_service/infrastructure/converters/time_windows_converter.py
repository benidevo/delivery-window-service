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
        # Keep track of which next-day closes have been used for overnight ranges
        used_next_day_closes: set[tuple[DayOfWeek, int]] = set()

        for day_name, time_windows in data.items():
            day_enum = day_mapping.get(day_name.lower())
            if day_enum is None:
                logger.warning(f"Unknown day name in data: {day_name}")
                continue

            windows = TimeWindowsConverter.process_day_windows(time_windows, day_name)

            if windows:
                schedule[day_enum] = DeliveryWindow(day_enum, windows)

        for i, day_enum in enumerate(day_enums):
            next_day_enum = day_enums[(i + 1) % len(day_enums)]
            day_name = day_name_map[day_enum].lower()
            next_day_name = day_name_map[next_day_enum].lower()

            current_day_events = data.get(day_name, [])
            next_day_events = data.get(next_day_name, [])

            if not current_day_events or not next_day_events:
                continue

            # Overnight pattern: last event today is 'open', first event tomorrow is 'close'. # noqa: E501
            last_event_current = current_day_events[-1]
            first_event_next = next_day_events[0]

            if "open" in last_event_current and "close" in first_event_next:
                close_key = (next_day_enum, first_event_next["close"])
                if close_key in used_next_day_closes:
                    continue

                open_seconds = last_event_current["open"]
                close_seconds = first_event_next["close"]

                try:
                    start_time = Time.from_unix_seconds(open_seconds)
                    end_time = Time.from_unix_seconds(close_seconds)

                    time_range = TimeRange(start_time, end_time)
                    existing_windows = schedule[day_enum].windows

                    logger.info(
                        "Creating and adding overnight range for "
                        f"{day_enum.name}: {time_range}"
                    )
                    new_windows = list(existing_windows) + [time_range]
                    schedule[day_enum] = DeliveryWindow(day_enum, new_windows)

                    used_next_day_closes.add(close_key)
                except Exception as e:
                    logger.warning(
                        "Error processing potential overnight range for "
                        f"{day_enum.name}: Open {open_seconds}s, "
                        f"Close {close_seconds}s. Error: {str(e)}",
                        exc_info=True,
                    )

        return schedule

    @staticmethod
    def process_day_windows(
        time_windows: list[dict[str, int]], day_name: str
    ) -> list[TimeRange]:
        """
        Processes time windows for a specific day and converts them
        to TimeRange objects.

        It takes a list of dictionaries representing opening and closing times,
        pairs them appropriately,
        and creates TimeRange objects from valid pairs. It also handles cases
        where closing times precede
        opening times (potential overnight windows) by skipping them since
        they will be handled in the `handle_all_days` method.
        """

        opens = []
        closes = []

        for i, window in enumerate(time_windows):
            if "open" in window:
                opens.append((i, window["open"]))
            elif "close" in window:
                closes.append((i, window["close"]))

        # Sort both by timestamp
        opens.sort(key=lambda x: x[1])
        closes.sort(key=lambda x: x[1])

        time_ranges = []
        processed_open_indices = set()
        open_idx = 0
        close_idx = 0

        while open_idx < len(opens) and close_idx < len(closes):
            open_index, open_time = opens[open_idx]
            _, close_time = closes[close_idx]

            if close_time < open_time:
                close_idx += 1
                logger.debug(
                    f"Skipping potential overnight pair for {day_name}: "
                    f"Open {open_time}s, Close {close_time}s"
                )
                continue

            try:
                start_time = Time.from_unix_seconds(open_time)
                end_time = Time.from_unix_seconds(close_time)
                time_range = TimeRange(start_time, end_time)
                time_ranges.append(time_range)
                logger.info(
                    f"Created within-day TimeRange for {day_name}: {time_range}"
                )
                processed_open_indices.add(open_index)
            except Exception as e:
                logger.warning(
                    f"Invalid time range detected for {day_name}: "
                    f"Open {open_time}s, Close {close_time}s. Error: {str(e)}"
                )

            # Move to next pair
            open_idx += 1
            close_idx += 1

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
