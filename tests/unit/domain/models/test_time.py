import pytest

from delivery_hours_service.domain.exceptions.time_exceptions import (
    InvalidTimeError,
)
from delivery_hours_service.domain.models.time import MINUTES_IN_DAY, Time


def test_should_create_time_when_valid_values_provided() -> None:
    time = Time(hours=14, minutes=30)

    assert time.hours == 14
    assert time.minutes == 30
    assert time.minutes_since_midnight == 14 * 60 + 30


def test_should_raise_error_when_hours_out_of_range() -> None:
    with pytest.raises(InvalidTimeError) as exc_info:
        Time(hours=24, minutes=0)

    assert "Hours must be between" in str(exc_info.value)


def test_should_raise_error_when_minutes_out_of_range() -> None:
    with pytest.raises(InvalidTimeError) as exc_info:
        Time(hours=14, minutes=60)

    assert "Minutes must be between" in str(exc_info.value)


def test_should_create_time_from_minutes_since_midnight() -> None:
    time = Time.from_minutes(minutes_since_midnight=870)  # 14:30

    assert time.hours == 14
    assert time.minutes == 30
    assert time.minutes_since_midnight == 870


def test_should_raise_when_minutes_since_midnight_out_of_range() -> None:
    with pytest.raises(InvalidTimeError) as exc_info:
        Time.from_minutes(minutes_since_midnight=MINUTES_IN_DAY)

    assert "Minutes since midnight must be between" in str(exc_info.value)


def test_should_create_time_from_unix_seconds() -> None:
    time = Time.from_unix_seconds(unix_seconds=52200)  # 14:30:00

    assert time.hours == 14
    assert time.minutes == 30
    assert time.minutes_since_midnight == 870


def test_should_raise_when_unix_seconds_out_of_range() -> None:
    with pytest.raises(InvalidTimeError) as exc_info:
        Time.from_unix_seconds(unix_seconds=86400)  # 24:00:00

    assert "Unix seconds must be between" in str(exc_info.value)


def test_should_add_minutes_correctly() -> None:
    time = Time(hours=14, minutes=30)
    new_time = time.add_minutes(minutes=90)  # +1:30

    assert new_time.hours == 16
    assert new_time.minutes == 0


def test_should_handle_day_wrap_when_subtracting_minutes() -> None:
    time = Time(hours=0, minutes=30)
    new_time = time.subtract_minutes(minutes=60)  # -1:00

    assert new_time.hours == 23
    assert new_time.minutes == 30


def test_should_format_time_without_minutes_when_minutes_are_zero() -> None:
    time = Time(hours=14, minutes=0)
    formatted = time.format()

    assert formatted == "14"


def test_should_format_time_with_minutes_when_minutes_not_zero() -> None:
    time = Time(hours=14, minutes=30)
    formatted = time.format()

    assert formatted == "14:30"


def test_should_compare_times_correctly() -> None:
    time1 = Time(hours=14, minutes=30)
    time2 = Time(hours=14, minutes=30)
    time3 = Time(hours=15, minutes=0)
    time4 = Time(hours=14, minutes=0)

    assert time1 == time2
    assert time1 != time3
    assert time1 > time4
    assert time1 < time3
    assert time4 < time1
