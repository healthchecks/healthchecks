from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from hc.api.models import Check


class CheckModelTestCase(TestCase):

    def test_it_strips_tags(self):
        check = Check()

        check.tags = " foo  bar "
        self.assertEqual(check.tags_list(), ["foo", "bar"])

        check.tags = " "
        self.assertEqual(check.tags_list(), [])

    def test_in_grace_period_handles_new_check(self):
        check = Check()
        self.assertFalse(check.in_grace_period())

    def test_status_works_with_grace_period(self):
        check = Check()
        check.status = "up"
        check.last_ping = timezone.now() - timedelta(days=1, minutes=30)

        self.assertTrue(check.in_grace_period())
        self.assertEqual(check.get_status(), "up")

    def test_paused_check_is_not_in_grace_period(self):
        check = Check()

        check.status = "up"
        check.last_ping = timezone.now() - timedelta(days=1, minutes=30)
        self.assertTrue(check.in_grace_period())

        check.status = "paused"
        self.assertFalse(check.in_grace_period())

    def test_status_works_with_cron_syntax(self):
        dt = timezone.make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

        # Expect ping every midnight, default grace is 1 hour
        check = Check()
        check.kind = "cron"
        check.schedule = "0 0 * * *"
        check.status = "up"
        check.last_ping = dt

        # 00:30am
        now = dt + timedelta(days=1, minutes=30)
        self.assertEqual(check.get_status(now), "up")

        # 1:30am
        now = dt + timedelta(days=1, minutes=90)
        self.assertEqual(check.get_status(now), "down")

    def test_status_works_with_timezone(self):
        dt = timezone.make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

        # Expect ping every day at 10am, default grace is 1 hour
        check = Check()
        check.kind = "cron"
        check.schedule = "0 10 * * *"
        check.status = "up"
        check.last_ping = dt
        check.tz = "Australia/Brisbane"  # UTC+10

        # 10:30am
        now = dt + timedelta(days=1, minutes=30)
        self.assertEqual(check.get_status(now), "up")

        # 11:30am
        now = dt + timedelta(days=1, minutes=90)
        self.assertEqual(check.get_status(now), "down")

    def test_next_ping_with_cron_syntax(self):
        dt = timezone.make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

        # Expect ping every round hour
        check = Check()
        check.kind = "cron"
        check.schedule = "0 * * * *"
        check.status = "up"
        check.last_ping = dt

        d = check.to_dict()
        self.assertEqual(d["next_ping"], "2000-01-01T01:00:00+00:00")
