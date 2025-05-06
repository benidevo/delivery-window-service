import pytest

from delivery_hours_service.domain.exceptions.time_exceptions import (
    IncompatibleDaysError,
)
from delivery_hours_service.domain.models.delivery_window import (
    DayOfWeek,
    DeliveryWindow,
)
from delivery_hours_service.domain.models.time import Time, TimeRange


def test_should_create_empty_delivery_window_when_no_windows_provided() -> None:
    delivery_window = DeliveryWindow(day=DayOfWeek.MONDAY)

    assert delivery_window.day == DayOfWeek.MONDAY
    assert delivery_window.windows == []
    assert delivery_window.is_closed


def test_should_create_closed_delivery_window() -> None:
    delivery_window = DeliveryWindow.closed(day=DayOfWeek.MONDAY)

    assert delivery_window.day == DayOfWeek.MONDAY
    assert delivery_window.is_closed


def test_should_create_delivery_window_with_time_ranges() -> None:
    time_range1 = TimeRange(
        start_time=Time(hours=10, minutes=0), end_time=Time(hours=12, minutes=0)
    )
    time_range2 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=16, minutes=0)
    )

    delivery_window = DeliveryWindow(
        day=DayOfWeek.MONDAY, windows=[time_range1, time_range2]
    )

    assert delivery_window.day == DayOfWeek.MONDAY
    assert len(delivery_window.windows) == 2
    assert not delivery_window.is_closed


def test_should_sort_time_ranges_by_start_time() -> None:
    time_range1 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=16, minutes=0)
    )
    time_range2 = TimeRange(
        start_time=Time(hours=10, minutes=0), end_time=Time(hours=12, minutes=0)
    )

    delivery_window = DeliveryWindow(
        day=DayOfWeek.MONDAY, windows=[time_range1, time_range2]
    )

    assert delivery_window.windows[0].start_time.hours == 10
    assert delivery_window.windows[1].start_time.hours == 14


def test_should_not_merge_non_overlapping_non_adjacent_ranges() -> None:
    time_range1 = TimeRange(
        start_time=Time(hours=10, minutes=0), end_time=Time(hours=12, minutes=0)
    )
    time_range2 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=16, minutes=0)
    )

    delivery_window = DeliveryWindow(
        day=DayOfWeek.MONDAY, windows=[time_range1, time_range2]
    )

    assert len(delivery_window.windows) == 2
    assert delivery_window.windows[0].start_time.hours == 10
    assert delivery_window.windows[0].end_time.hours == 12
    assert delivery_window.windows[1].start_time.hours == 14
    assert delivery_window.windows[1].end_time.hours == 16


def test_should_handle_multiple_merges_in_complex_case() -> None:
    ranges = [
        TimeRange(Time(8, 0), Time(10, 0)),  # 8-10
        TimeRange(Time(12, 0), Time(14, 0)),  # 12-14
        TimeRange(Time(9, 0), Time(13, 0)),  # 9-13 (overlaps with both previous)
        TimeRange(Time(16, 0), Time(18, 0)),  # 16-18
        TimeRange(Time(18, 0), Time(20, 0)),  # 18-20 (adjacent to previous)
    ]

    delivery_window = DeliveryWindow(day=DayOfWeek.MONDAY, windows=ranges)

    assert len(delivery_window.windows) == 2
    assert delivery_window.windows[0].start_time.hours == 8
    assert delivery_window.windows[0].end_time.hours == 14
    assert delivery_window.windows[1].start_time.hours == 16
    assert delivery_window.windows[1].end_time.hours == 20


def test_should_intersect_two_delivery_windows() -> None:
    window1 = DeliveryWindow(
        day=DayOfWeek.MONDAY,
        windows=[
            TimeRange(Time(10, 0), Time(12, 0)),
            TimeRange(Time(14, 0), Time(16, 0)),
        ],
    )

    window2 = DeliveryWindow(
        day=DayOfWeek.MONDAY, windows=[TimeRange(Time(11, 0), Time(15, 0))]
    )

    intersection = window1.intersect_with(window2)

    assert intersection.day == DayOfWeek.MONDAY
    assert len(intersection.windows) == 2
    assert intersection.windows[0].start_time.hours == 11
    assert intersection.windows[0].end_time.hours == 12
    assert intersection.windows[1].start_time.hours == 14
    assert intersection.windows[1].end_time.hours == 15


def test_should_raise_when_intersecting_different_days() -> None:
    window1 = DeliveryWindow(day=DayOfWeek.MONDAY)
    window2 = DeliveryWindow(day=DayOfWeek.TUESDAY)

    with pytest.raises(IncompatibleDaysError) as exc_info:
        window1.intersect_with(window2)

    assert "Cannot intersect different days" in str(exc_info.value)


def test_should_return_closed_window_when_either_input_is_closed() -> None:
    window1 = DeliveryWindow(
        day=DayOfWeek.MONDAY,
        windows=[
            TimeRange(Time(10, 0), Time(12, 0)),
            TimeRange(Time(14, 0), Time(16, 0)),
        ],
    )

    window2 = DeliveryWindow.closed(day=DayOfWeek.MONDAY)

    intersection = window1.intersect_with(window2)

    assert intersection.is_closed


def test_should_format_closed_delivery_window() -> None:
    window = DeliveryWindow.closed(day=DayOfWeek.MONDAY)

    assert window.format() == "Closed"


def test_should_format_delivery_window_with_multiple_ranges() -> None:
    window = DeliveryWindow(
        day=DayOfWeek.MONDAY,
        windows=[
            TimeRange(Time(10, 0), Time(12, 0)),
            TimeRange(Time(14, 0), Time(16, 30)),
        ],
    )

    assert window.format() == "10-12, 14-16:30"
