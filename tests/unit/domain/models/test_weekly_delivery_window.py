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


def test_should_create_weekly_window_with_specified_days() -> None:
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


def test_should_intersect_two_weekly_windows() -> None:
    # First window: Monday 10-16, Tuesday 12-14
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
