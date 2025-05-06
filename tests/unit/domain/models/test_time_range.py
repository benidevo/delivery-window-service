import pytest

from delivery_hours_service.domain.exceptions.time_exceptions import (
    InvalidDurationError,
)
from delivery_hours_service.domain.models.time import (
    MINIMUM_DURATION_MINUTES,
    Time,
    TimeRange,
)


def test_should_create_time_range_when_valid_values_provided() -> None:
    start_time = Time(hours=14, minutes=0)
    end_time = Time(hours=16, minutes=0)
    time_range = TimeRange(start_time=start_time, end_time=end_time)

    assert time_range.start_time == start_time
    assert time_range.end_time == end_time
    assert time_range.duration_minutes == 120
    assert not time_range.is_overnight


def test_should_detect_overnight_when_end_before_start() -> None:
    start_time = Time(hours=22, minutes=0)
    end_time = Time(hours=2, minutes=0)
    time_range = TimeRange(start_time=start_time, end_time=end_time)

    assert time_range.is_overnight
    assert time_range.duration_minutes == 240  # 4 hours


def test_should_raise_when_duration_less_than_minimum() -> None:
    start_time = Time(hours=14, minutes=0)
    end_time = Time(hours=14, minutes=29)  # 29 min duration (less than 30)

    with pytest.raises(InvalidDurationError) as exc_info:
        TimeRange(start_time=start_time, end_time=end_time)

    assert "Duration must be at least" in str(exc_info.value)
    assert f"{MINIMUM_DURATION_MINUTES}" in str(exc_info.value)


def test_should_detect_time_containment_in_regular_range() -> None:
    time_range = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=16, minutes=0)
    )

    # Times within range
    assert time_range.contains_time(Time(hours=14, minutes=0))
    assert time_range.contains_time(Time(hours=15, minutes=0))
    assert time_range.contains_time(Time(hours=16, minutes=0))

    # Times outside range
    assert not time_range.contains_time(Time(hours=13, minutes=59))
    assert not time_range.contains_time(Time(hours=16, minutes=1))


def test_should_detect_time_containment_in_overnight_range() -> None:
    time_range = TimeRange(
        start_time=Time(hours=22, minutes=0), end_time=Time(hours=2, minutes=0)
    )

    # Times within range
    assert time_range.contains_time(Time(hours=22, minutes=0))
    assert time_range.contains_time(Time(hours=23, minutes=0))
    assert time_range.contains_time(Time(hours=0, minutes=0))
    assert time_range.contains_time(Time(hours=1, minutes=0))
    assert time_range.contains_time(Time(hours=2, minutes=0))

    # Times outside range
    assert not time_range.contains_time(Time(hours=3, minutes=0))
    assert not time_range.contains_time(Time(hours=21, minutes=0))


def test_should_detect_overlap_between_regular_ranges() -> None:
    range1 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=16, minutes=0)
    )

    # Overlapping ranges
    range2 = TimeRange(
        start_time=Time(hours=15, minutes=0), end_time=Time(hours=17, minutes=0)
    )
    assert range1.overlaps_with(range2)
    assert range2.overlaps_with(range1)

    # Non-overlapping ranges
    range3 = TimeRange(
        start_time=Time(hours=16, minutes=30), end_time=Time(hours=18, minutes=0)
    )
    assert not range1.overlaps_with(range3)
    assert not range3.overlaps_with(range1)


def test_should_detect_overlap_with_overnight_ranges() -> None:
    overnight_range = TimeRange(
        start_time=Time(hours=22, minutes=0), end_time=Time(hours=2, minutes=0)
    )

    # Regular range overlapping with overnight range
    day_range = TimeRange(
        start_time=Time(hours=1, minutes=0), end_time=Time(hours=3, minutes=0)
    )
    assert overnight_range.overlaps_with(day_range)
    assert day_range.overlaps_with(overnight_range)

    # Two overnight ranges always overlap
    other_overnight = TimeRange(
        start_time=Time(hours=23, minutes=0), end_time=Time(hours=5, minutes=0)
    )
    assert overnight_range.overlaps_with(other_overnight)
    assert other_overnight.overlaps_with(overnight_range)


def test_should_merge_overlapping_regular_ranges() -> None:
    range1 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=16, minutes=0)
    )
    range2 = TimeRange(
        start_time=Time(hours=15, minutes=0), end_time=Time(hours=17, minutes=0)
    )

    merged = range1.merge(range2)

    assert merged is not None
    assert merged.start_time.hours == 14
    assert merged.start_time.minutes == 0
    assert merged.end_time.hours == 17
    assert merged.end_time.minutes == 0


def test_should_not_merge_non_overlapping_non_adjacent_ranges() -> None:
    range1 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=16, minutes=0)
    )
    range2 = TimeRange(
        start_time=Time(hours=17, minutes=0), end_time=Time(hours=18, minutes=0)
    )

    merged = range1.merge(range2)

    assert merged is None


def test_should_prefer_larger_overnight_range_when_merging() -> None:
    overnight1 = TimeRange(
        start_time=Time(hours=22, minutes=0), end_time=Time(hours=2, minutes=0)
    )  # 4 hours
    overnight2 = TimeRange(
        start_time=Time(hours=21, minutes=0), end_time=Time(hours=3, minutes=0)
    )  # 6 hours

    merged = overnight1.merge(overnight2)

    assert merged is not None
    assert merged.start_time.hours == 21
    assert merged.end_time.hours == 3


def test_should_find_intersection_of_regular_ranges() -> None:
    range1 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=16, minutes=0)
    )
    range2 = TimeRange(
        start_time=Time(hours=15, minutes=0), end_time=Time(hours=17, minutes=0)
    )

    intersection = range1.find_intersection(range2)

    assert intersection is not None
    assert intersection.start_time.hours == 15
    assert intersection.start_time.minutes == 0
    assert intersection.end_time.hours == 16
    assert intersection.end_time.minutes == 0


def test_should_return_none_when_intersection_too_short() -> None:
    range1 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=15, minutes=0)
    )
    range2 = TimeRange(
        start_time=Time(hours=14, minutes=40), end_time=Time(hours=16, minutes=0)
    )

    # Intersection would be 14:40-15:00 (20 min), but minimum is 30 min
    intersection = range1.find_intersection(range2)

    assert intersection is None


def test_should_return_none_when_no_intersection() -> None:
    range1 = TimeRange(
        start_time=Time(hours=14, minutes=0), end_time=Time(hours=15, minutes=0)
    )
    range2 = TimeRange(
        start_time=Time(hours=16, minutes=0), end_time=Time(hours=17, minutes=0)
    )

    intersection = range1.find_intersection(range2)

    assert intersection is None
