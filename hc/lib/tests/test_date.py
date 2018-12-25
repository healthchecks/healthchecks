from datetime import timedelta as td
from django.test import TestCase

from hc.lib.date import format_mins_secs


class DateFormattingTestCase(TestCase):

    def test_mins_secs_work(self):
        s = format_mins_secs(td(seconds=0))
        self.assertEqual(s, "0 sec")

        s = format_mins_secs(td(seconds=1))
        self.assertEqual(s, "1 sec")

        s = format_mins_secs(td(seconds=61))
        self.assertEqual(s, "1 min 1 sec")

        s = format_mins_secs(td(seconds=62))
        self.assertEqual(s, "1 min 2 sec")
