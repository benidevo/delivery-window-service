from delivery_hours_service.domain.models.delivery_window import (
    DayOfWeek,
    WeeklyDeliveryWindow,
)
from delivery_hours_service.infrastructure.converters.time_windows_converter import (
    TimeWindowsConverter,
)


def test_convert_to_weekly_delivery_window_should_handle_empty_response() -> None:
    data: dict[str, list[dict[str, int]]] = {}

    result = TimeWindowsConverter.convert_to_weekly_delivery_window(data)

    assert isinstance(result, WeeklyDeliveryWindow)
    assert len(result.schedule) == 7
    assert all(day_window.is_closed for day_window in result.schedule.values())


def test_convert_to_weekly_delivery_window_should_handle_valid_data() -> None:
    data = {
        "monday": [
            {"open": 36000},  # 10:00
            {"close": 50400},  # 14:00
        ],
    }

    result = TimeWindowsConverter.convert_to_weekly_delivery_window(data)

    assert isinstance(result, WeeklyDeliveryWindow)
    assert not result.schedule[DayOfWeek.MONDAY].is_closed
    assert len(result.schedule[DayOfWeek.MONDAY].windows) == 1
    assert result.schedule[DayOfWeek.MONDAY].windows[0].start_time.hours == 10
    assert result.schedule[DayOfWeek.MONDAY].windows[0].end_time.hours == 14


def test_convert_to_weekly_delivery_window_should_handle_multiple_windows_per_day() -> (
    None
):
    data = {
        "monday": [
            {"open": 36000},  # 10:00
            {"close": 50400},  # 14:00
            {"open": 57600},  # 16:00
            {"close": 72000},  # 20:00
        ],
    }

    result = TimeWindowsConverter.convert_to_weekly_delivery_window(data)

    assert len(result.schedule[DayOfWeek.MONDAY].windows) == 2
    assert result.schedule[DayOfWeek.MONDAY].windows[0].start_time.hours == 10
    assert result.schedule[DayOfWeek.MONDAY].windows[0].end_time.hours == 14
    assert result.schedule[DayOfWeek.MONDAY].windows[1].start_time.hours == 16
    assert result.schedule[DayOfWeek.MONDAY].windows[1].end_time.hours == 20


def test_process_day_windows_should_handle_mismatched_open_close_counts() -> None:
    time_windows = [
        {"open": 36000},  # 10:00
        {"close": 50400},  # 14:00
        {"open": 57600},  # 16:00
        # Missing close for the second open
    ]

    result = TimeWindowsConverter.process_day_windows(time_windows, "monday")

    assert len(result) == 1
    assert result[0].start_time.hours == 10
    assert result[0].end_time.hours == 14


def test_process_day_windows_should_handle_extra_close_entries() -> None:
    time_windows = [
        {"close": 32400},  # 9:00 - extra close with no matching open
        {"open": 36000},  # 10:00
        {"close": 50400},  # 14:00
    ]

    result = TimeWindowsConverter.process_day_windows(time_windows, "monday")

    assert len(result) == 1
    assert result[0].start_time.hours == 10
    assert result[0].end_time.hours == 14


def test_get_day_mapping_should_return_correct_mapping() -> None:
    mapping = TimeWindowsConverter.get_day_mapping()

    assert mapping["monday"] == DayOfWeek.MONDAY
    assert mapping["tuesday"] == DayOfWeek.TUESDAY
    assert mapping["wednesday"] == DayOfWeek.WEDNESDAY
    assert mapping["thursday"] == DayOfWeek.THURSDAY
    assert mapping["friday"] == DayOfWeek.FRIDAY
    assert mapping["saturday"] == DayOfWeek.SATURDAY
    assert mapping["sunday"] == DayOfWeek.SUNDAY
