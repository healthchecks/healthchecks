from __future__ import annotations

from datetime import date, datetime
from datetime import timedelta as td
from datetime import timezone
from unittest import TestCase
from unittest.mock import Mock, patch

from hc.lib.date import (
    format_approx_duration,
    format_hms,
    month_boundaries,
    seconds_in_month,
    week_boundaries,
)

CURRENT_TIME = datetime(2020, 1, 15, tzinfo=timezone.utc)
MOCK_NOW = Mock(return_value=CURRENT_TIME)


class DateFormattingTestCase(TestCase):
    def test_sub_second_works(self) -> None:
        s = format_hms(td(seconds=0.12))
        self.assertEqual(s, "0.12 sec")

    def test_mins_secs_work(self) -> None:
        s = format_hms(td(seconds=0))
        self.assertEqual(s, "0 sec")

        s = format_hms(td(seconds=1))
        self.assertEqual(s, "1 sec")

        s = format_hms(td(seconds=61))
        self.assertEqual(s, "1 min 1 sec")

        s = format_hms(td(seconds=62))
        self.assertEqual(s, "1 min 2 sec")

    def test_hours_work(self) -> None:
        s = format_hms(td(seconds=62 + 60 * 60))
        self.assertEqual(s, "1 h 1 min 2 sec")

        s = format_hms(td(seconds=60 * 60))
        self.assertEqual(s, "1 h 0 min 0 sec")


class ApproxFormattingTestCase(TestCase):
    def test_days_work(self) -> None:
        s = format_approx_duration(td(days=3, hours=6, minutes=12, seconds=24))
        self.assertEqual(s, "3 days 6 h")

    def test_one_day_works(self) -> None:
        s = format_approx_duration(td(days=1, hours=6, minutes=12, seconds=24))
        self.assertEqual(s, "1 day 6 h")

    def test_hours_work(self) -> None:
        s = format_approx_duration(td(hours=6, minutes=12, seconds=24))
        self.assertEqual(s, "6 h 12 min")

    def test_minutes_work(self) -> None:
        s = format_approx_duration(td(minutes=12, seconds=24))
        self.assertEqual(s, "12 min 24 sec")


@patch("hc.lib.date.now", MOCK_NOW)
class MonthBoundaryTestCase(TestCase):
    def test_utc_works(self) -> None:
        result = month_boundaries(3, "UTC")
        self.assertEqual(result[0].isoformat(), "2020-01-01T00:00:00+00:00")
        self.assertEqual(result[1].isoformat(), "2019-12-01T00:00:00+00:00")
        self.assertEqual(result[2].isoformat(), "2019-11-01T00:00:00+00:00")

    def test_non_utc_works(self) -> None:
        result = month_boundaries(3, "Europe/Riga")
        self.assertEqual(result[0].isoformat(), "2020-01-01T00:00:00+02:00")
        self.assertEqual(result[1].isoformat(), "2019-12-01T00:00:00+02:00")
        self.assertEqual(result[2].isoformat(), "2019-11-01T00:00:00+02:00")


@patch("hc.lib.date.now", MOCK_NOW)
class WeekBoundaryTestCase(TestCase):
    def test_utc_works(self) -> None:
        result = week_boundaries(3, "UTC")
        self.assertEqual(result[0].isoformat(), "2020-01-13T00:00:00+00:00")
        self.assertEqual(result[1].isoformat(), "2020-01-06T00:00:00+00:00")
        self.assertEqual(result[2].isoformat(), "2019-12-30T00:00:00+00:00")

    def test_non_utc_works(self) -> None:
        result = week_boundaries(3, "Europe/Riga")
        self.assertEqual(result[0].isoformat(), "2020-01-13T00:00:00+02:00")
        self.assertEqual(result[1].isoformat(), "2020-01-06T00:00:00+02:00")
        self.assertEqual(result[2].isoformat(), "2019-12-30T00:00:00+02:00")


class SecondsInMonthTestCase(TestCase):
    def test_utc_works(self) -> None:
        result = seconds_in_month(date(2023, 10, 1), "UTC")
        self.assertEqual(result, 31 * 24 * 60 * 60)

    def test_it_handles_dst_extra_hour(self) -> None:
        result = seconds_in_month(date(2023, 10, 1), "Europe/Riga")
        self.assertEqual(result, 31 * 24 * 60 * 60 + 60 * 60)

    def test_it_handles_dst_skipped_hour(self) -> None:
        result = seconds_in_month(date(2024, 3, 1), "Europe/Riga")
        self.assertEqual(result, 31 * 24 * 60 * 60 - 60 * 60)
