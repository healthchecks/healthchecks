from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from unittest import TestCase
from unittest.mock import Mock, patch

from hc.lib.date import format_hms, month_boundaries, week_boundaries

CURRENT_TIME = datetime(2020, 1, 15, tzinfo=timezone.utc)
MOCK_NOW = Mock(return_value=CURRENT_TIME)


class DateFormattingTestCase(TestCase):
    def test_sub_second_works(self):
        s = format_hms(td(seconds=0.12))
        self.assertEqual(s, "0.12 sec")

    def test_mins_secs_work(self):
        s = format_hms(td(seconds=0))
        self.assertEqual(s, "0 sec")

        s = format_hms(td(seconds=1))
        self.assertEqual(s, "1 sec")

        s = format_hms(td(seconds=61))
        self.assertEqual(s, "1 min 1 sec")

        s = format_hms(td(seconds=62))
        self.assertEqual(s, "1 min 2 sec")

    def test_hours_work(self):
        s = format_hms(td(seconds=62 + 60 * 60))
        self.assertEqual(s, "1 h 1 min 2 sec")

        s = format_hms(td(seconds=60 * 60))
        self.assertEqual(s, "1 h 0 min 0 sec")


@patch("hc.lib.date.now", MOCK_NOW)
class MonthBoundaryTestCase(TestCase):
    def test_utc_works(self):
        result = month_boundaries(3, "UTC")
        self.assertEqual(result[0].isoformat(), "2019-11-01T00:00:00+00:00")
        self.assertEqual(result[1].isoformat(), "2019-12-01T00:00:00+00:00")
        self.assertEqual(result[2].isoformat(), "2020-01-01T00:00:00+00:00")

    def test_non_utc_works(self):
        result = month_boundaries(3, "Europe/Riga")
        self.assertEqual(result[0].isoformat(), "2019-11-01T00:00:00+02:00")
        self.assertEqual(result[1].isoformat(), "2019-12-01T00:00:00+02:00")
        self.assertEqual(result[2].isoformat(), "2020-01-01T00:00:00+02:00")


@patch("hc.lib.date.now", MOCK_NOW)
class WeekBoundaryTestCase(TestCase):
    def test_utc_works(self):
        result = week_boundaries(3, "UTC")
        self.assertEqual(result[0].isoformat(), "2019-12-30T00:00:00+00:00")
        self.assertEqual(result[1].isoformat(), "2020-01-06T00:00:00+00:00")
        self.assertEqual(result[2].isoformat(), "2020-01-13T00:00:00+00:00")

    def test_non_utc_works(self):
        result = week_boundaries(3, "Europe/Riga")
        self.assertEqual(result[0].isoformat(), "2019-12-30T00:00:00+02:00")
        self.assertEqual(result[1].isoformat(), "2020-01-06T00:00:00+02:00")
        self.assertEqual(result[2].isoformat(), "2020-01-13T00:00:00+02:00")
