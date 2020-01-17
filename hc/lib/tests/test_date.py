from datetime import datetime as dt, timedelta as td
from django.test import TestCase

from hc.lib.date import format_hms, choose_next_report_date


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


class NextReportDateTestCase(TestCase):
    def test_it_works(self):
        # October
        nao = dt(year=2019, month=10, day=15, hour=6)
        result = choose_next_report_date(nao)
        self.assertEqual(result.year, 2019)
        self.assertEqual(result.month, 11)
        self.assertEqual(result.day, 1)
        self.assertTrue(result.hour >= 12)

        # December
        nao = dt(year=2019, month=12, day=15, hour=6)
        result = choose_next_report_date(nao)
        self.assertEqual(result.year, 2020)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)
        self.assertTrue(result.hour >= 12)
