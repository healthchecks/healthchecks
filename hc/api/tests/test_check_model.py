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

    def test_get_status_handles_new_check(self):
        check = Check()
        self.assertEqual(check.get_status(), "new")

    def test_status_works_with_grace_period(self):
        check = Check()
        check.status = "up"
        check.last_ping = timezone.now() - timedelta(days=1, minutes=30)

        self.assertEqual(check.get_status(), "grace")

    def test_get_status_handles_paused_check(self):
        check = Check()

        check.status = "up"
        check.last_ping = timezone.now() - timedelta(days=1, minutes=30)
        self.assertEqual(check.get_status(), "grace")

        check.status = "paused"
        self.assertEqual(check.get_status(), "paused")

    def test_status_works_with_cron_syntax(self):
        dt = timezone.make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

        # Expect ping every midnight, default grace is 1 hour
        check = Check()
        check.kind = "cron"
        check.schedule = "0 0 * * *"
        check.status = "up"
        check.last_ping = dt

        # 23:59pm
        now = dt + timedelta(hours=23, minutes=59)
        self.assertEqual(check.get_status(now), "up")

        # 00:00am
        now = dt + timedelta(days=1)
        self.assertEqual(check.get_status(now), "grace")

        # 1:30am
        now = dt + timedelta(days=1, minutes=60)
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
        now = dt + timedelta(hours=23, minutes=59)
        self.assertEqual(check.get_status(now), "up")

        # 10:30am
        now = dt + timedelta(days=1)
        self.assertEqual(check.get_status(now), "grace")

        # 11:30am
        now = dt + timedelta(days=1, minutes=60)
        self.assertEqual(check.get_status(now), "down")

    def test_get_status_handles_past_grace(self):
        check = Check()
        check.status = "up"
        check.last_ping = timezone.now() - timedelta(days=2)

        self.assertEqual(check.get_status(), "down")

    def test_get_status_obeys_down_status(self):
        check = Check()
        check.status = "down"
        check.last_ping = timezone.now() - timedelta(minutes=1)

        self.assertEqual(check.get_status(), "down")

    def test_get_status_handles_started(self):
        check = Check()
        check.last_ping = timezone.now() - timedelta(hours=2)
        check.last_start = timezone.now() - timedelta(minutes=5)
        for status in ("new", "paused", "up", "down"):
            check.status = status
            self.assertEqual(check.get_status(), "started")

    def test_get_status_handles_started_and_mia(self):
        check = Check()
        check.last_start = timezone.now() - timedelta(hours=2)
        self.assertEqual(check.get_status(), "down")

    def test_next_ping_with_cron_syntax(self):
        dt = timezone.make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

        # Expect ping every round hour
        check = Check()
        check.kind = "cron"
        check.schedule = "0 * * * *"
        check.status = "up"
        check.last_ping = dt
        check.save()

        d = check.to_dict()
        self.assertEqual(d["next_ping"], "2000-01-01T01:00:00+00:00")
