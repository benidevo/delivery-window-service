from delivery_hours_service.domain.models.delivery_window import (
    DayOfWeek,
    DeliveryWindow,
    WeeklyDeliveryWindow,
)
from delivery_hours_service.domain.models.time import Time, TimeRange


def test_should_create_empty_weekly_window() -> None:
    weekly_window = WeeklyDeliveryWindow.empty()
    for day in DayOfWeek:
        assert weekly_window.get_day_window(day).is_closed
    assert weekly_window.is_empty()

    monday_window = DeliveryWindow(
        day=DayOfWeek.MONDAY,
        windows=[
            TimeRange(Time(10, 0), Time(12, 0)),
            TimeRange(Time(14, 0), Time(16, 0)),
        ],
    )
    weekly_window = WeeklyDeliveryWindow(schedule={DayOfWeek.MONDAY: monday_window})

    # Monday should have windows
    monday = weekly_window.get_day_window(DayOfWeek.MONDAY)
    assert not monday.is_closed
    assert len(monday.windows) == 2

    # Other days should be closed
    for day in DayOfWeek:
        if day != DayOfWeek.MONDAY:
            assert weekly_window.get_day_window(day).is_closed

    # Should not be empty when at least one day has windows
    assert not weekly_window.is_empty()


def test_should_intersect_two_weekly_windows() -> None:
    window1 = WeeklyDeliveryWindow(
        schedule={
            DayOfWeek.MONDAY: DeliveryWindow(
                day=DayOfWeek.MONDAY, windows=[TimeRange(Time(10, 0), Time(16, 0))]
            ),
            DayOfWeek.TUESDAY: DeliveryWindow(
                day=DayOfWeek.TUESDAY, windows=[TimeRange(Time(12, 0), Time(14, 0))]
            ),
        }
    )

    # Second window: Monday 12-18, Tuesday 10-16
    window2 = WeeklyDeliveryWindow(
        schedule={
            DayOfWeek.MONDAY: DeliveryWindow(
                day=DayOfWeek.MONDAY, windows=[TimeRange(Time(12, 0), Time(18, 0))]
            ),
            DayOfWeek.TUESDAY: DeliveryWindow(
                day=DayOfWeek.TUESDAY, windows=[TimeRange(Time(10, 0), Time(16, 0))]
            ),
        }
    )

    intersection = window1.intersect_with(window2)

    # Monday should be 12-16
    monday = intersection.get_day_window(DayOfWeek.MONDAY)
    assert len(monday.windows) == 1
    assert monday.windows[0].start_time.hours == 12
    assert monday.windows[0].end_time.hours == 16

    # Tuesday should be 12-14
    tuesday = intersection.get_day_window(DayOfWeek.TUESDAY)
    assert len(tuesday.windows) == 1
    assert tuesday.windows[0].start_time.hours == 12
    assert tuesday.windows[0].end_time.hours == 14

    # Other days should be closed
    for day in DayOfWeek:
        if day not in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY]:
            assert intersection.get_day_window(day).is_closed


def test_should_get_schedule_data() -> None:
    monday_window = DeliveryWindow(
        day=DayOfWeek.MONDAY,
        windows=[
            TimeRange(Time(10, 0), Time(12, 0)),
            TimeRange(Time(14, 0), Time(16, 0)),
        ],
    )
    weekly_window = WeeklyDeliveryWindow(schedule={DayOfWeek.MONDAY: monday_window})

    schedule_data = weekly_window.get_schedule_data()

    # Check Monday data
    assert DayOfWeek.MONDAY in schedule_data
    assert len(schedule_data[DayOfWeek.MONDAY]) == 2

    # Check first time range
    start_time, end_time = schedule_data[DayOfWeek.MONDAY][0]
    assert start_time.hours == 10
    assert start_time.minutes == 0
    assert end_time.hours == 12
    assert end_time.minutes == 0

    # Check second time range
    start_time, end_time = schedule_data[DayOfWeek.MONDAY][1]
    assert start_time.hours == 14
    assert start_time.minutes == 0
    assert end_time.hours == 16
    assert end_time.minutes == 0

    # Check other days are empty
    for day in DayOfWeek:
        if day != DayOfWeek.MONDAY:
            assert len(schedule_data[day]) == 0
