from datetime import timedelta as td
from django.test import TestCase

from hc.lib.date import format_hms


class DateFormattingTestCase(TestCase):
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
