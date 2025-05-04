from delivery_hours_service.domain.models.delivery_window import DayOfWeek
from delivery_hours_service.infrastructure.converters.time_windows_converter import (
    TimeWindowsConverter,
)


def test_converter_should_handle_cross_day_windows() -> None:
    data = {
        "monday": [
            {"open": 28800},  # 8:00
            {"close": 72000},  # 20:00
        ],
        "wednesday": [
            {"open": 72000},  # 20:00 (no matching close - should extend to Thursday)
        ],
        "thursday": [
            {"close": 3600},  # 1:00 (matches with Wednesday's opening)
            {"open": 28800},  # 8:00
            {"close": 52200},  # 14:30
            {"open": 57600},  # 16:00
            {"close": 72000},  # 20:00
        ],
    }

    result = TimeWindowsConverter.convert_to_weekly_delivery_window(data)

    # Monday: 8-20
    assert not result.schedule[DayOfWeek.MONDAY].is_closed
    assert len(result.schedule[DayOfWeek.MONDAY].windows) == 1
    assert result.schedule[DayOfWeek.MONDAY].windows[0].start_time.hours == 8
    assert result.schedule[DayOfWeek.MONDAY].windows[0].end_time.hours == 20

    # Tuesday: Closed
    assert result.schedule[DayOfWeek.TUESDAY].is_closed

    # Wednesday: 20-00 (overnight to Thursday)
    assert not result.schedule[DayOfWeek.WEDNESDAY].is_closed
    assert len(result.schedule[DayOfWeek.WEDNESDAY].windows) == 1
    assert result.schedule[DayOfWeek.WEDNESDAY].windows[0].start_time.hours == 20
    assert result.schedule[DayOfWeek.WEDNESDAY].windows[0].start_time.minutes == 0
    assert result.schedule[DayOfWeek.WEDNESDAY].windows[0].is_overnight

    # Thursday: 8-14:30, 16-20
    assert not result.schedule[DayOfWeek.THURSDAY].is_closed
    assert len(result.schedule[DayOfWeek.THURSDAY].windows) == 2

    # First window: 8-14:30
    assert result.schedule[DayOfWeek.THURSDAY].windows[0].start_time.hours == 8
    assert result.schedule[DayOfWeek.THURSDAY].windows[0].end_time.hours == 14
    assert result.schedule[DayOfWeek.THURSDAY].windows[0].end_time.minutes == 30

    # Second window: 16-20
    assert result.schedule[DayOfWeek.THURSDAY].windows[1].start_time.hours == 16
    assert result.schedule[DayOfWeek.THURSDAY].windows[1].end_time.hours == 20

    # Other days should be closed
    assert result.schedule[DayOfWeek.FRIDAY].is_closed
    assert result.schedule[DayOfWeek.SATURDAY].is_closed
    assert result.schedule[DayOfWeek.SUNDAY].is_closed


def test_converter_should_handle_multiple_cross_day_windows() -> None:
    data = {
        "monday": [
            {"open": 72000},  # 20:00 (no matching close - extends to Tuesday)
        ],
        "tuesday": [
            {"close": 3600},  # 1:00 (matches Monday's opening)
            {"open": 72000},  # 20:00 (extends to Wednesday)
        ],
        "wednesday": [
            {"close": 3600},  # 1:00 (matches Tuesday's opening)
        ],
    }

    result = TimeWindowsConverter.convert_to_weekly_delivery_window(data)

    # Monday: 20-00 (overnight)
    assert not result.schedule[DayOfWeek.MONDAY].is_closed
    assert len(result.schedule[DayOfWeek.MONDAY].windows) == 1
    assert result.schedule[DayOfWeek.MONDAY].windows[0].start_time.hours == 20
    assert result.schedule[DayOfWeek.MONDAY].windows[0].is_overnight

    # Tuesday: 20-00 (overnight)
    assert not result.schedule[DayOfWeek.TUESDAY].is_closed
    assert len(result.schedule[DayOfWeek.TUESDAY].windows) == 1
    assert result.schedule[DayOfWeek.TUESDAY].windows[0].start_time.hours == 20
    assert result.schedule[DayOfWeek.TUESDAY].windows[0].is_overnight

    # Wednesday should be closed
    assert result.schedule[DayOfWeek.WEDNESDAY].is_closed
