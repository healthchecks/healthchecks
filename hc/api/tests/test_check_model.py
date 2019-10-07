from datetime import datetime, timedelta

from django.utils import timezone
from hc.api.models import Check, Flip
from hc.test import BaseTestCase
from mock import patch


class CheckModelTestCase(BaseTestCase):
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
        # Last start was 5 minutes ago, display status should be "started"
        check.last_start = timezone.now() - timedelta(minutes=5)
        for status in ("new", "paused", "up", "down"):
            check.status = status
            self.assertEqual(check.get_status(), "started")

    def test_get_status_handles_down_then_started_and_expired(self):
        check = Check(status="down")
        # Last ping was 2 days ago
        check.last_ping = timezone.now() - timedelta(days=2)
        # Last start was 2 hours ago - the check is past its grace time
        check.last_start = timezone.now() - timedelta(hours=2)

        self.assertEqual(check.get_status(), "down")
        self.assertEqual(check.get_status(with_started=False), "down")

    def test_get_status_handles_up_then_started(self):
        check = Check(status="up")
        # Last ping was 2 hours ago, so is still up
        check.last_ping = timezone.now() - timedelta(hours=2)
        # Last start was 5 minutes ago
        check.last_start = timezone.now() - timedelta(minutes=5)

        self.assertEqual(check.get_status(), "started")
        # Starting a check starts the grace period:
        self.assertEqual(check.get_status(with_started=False), "grace")

    def test_get_status_handles_up_then_started_and_expired(self):
        check = Check(status="up")
        # Last ping was 3 hours ago, so is still up
        check.last_ping = timezone.now() - timedelta(hours=3)
        # Last start was 2 hours ago - the check is past its grace time
        check.last_start = timezone.now() - timedelta(hours=2)

        self.assertEqual(check.get_status(), "down")
        self.assertEqual(check.get_status(with_started=False), "down")

    def test_get_status_handles_paused_then_started_and_expired(self):
        check = Check(status="paused")
        # Last start was 2 hours ago - the check is past its grace time
        check.last_start = timezone.now() - timedelta(hours=2)

        self.assertEqual(check.get_status(), "down")
        self.assertEqual(check.get_status(with_started=False), "down")

    def test_get_status_handles_started_and_mia(self):
        check = Check()
        check.last_start = timezone.now() - timedelta(hours=2)

        self.assertEqual(check.get_status(), "down")
        self.assertEqual(check.get_status(with_started=False), "down")

    def test_next_ping_with_cron_syntax(self):
        dt = timezone.make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

        # Expect ping every round hour
        check = Check(project=self.project)
        check.kind = "cron"
        check.schedule = "0 * * * *"
        check.status = "up"
        check.last_ping = dt
        # Need to save it for M2M relations to work:
        check.save()

        d = check.to_dict()
        self.assertEqual(d["next_ping"], "2000-01-01T01:00:00+00:00")

    def test_downtimes_handles_no_flips(self):
        check = Check.objects.create(project=self.project)
        r = check.downtimes(10)
        self.assertEqual(len(r), 10)
        for dt, downtime, outages in r:
            self.assertEqual(downtime.total_seconds(), 0)
            self.assertEqual(outages, 0)

    def test_downtimes_handles_currently_down_check(self):
        check = Check.objects.create(project=self.project, status="down")

        r = check.downtimes(10)
        self.assertEqual(len(r), 10)
        for dt, downtime, outages in r:
            self.assertEqual(outages, 1)

    @patch("hc.api.models.timezone.now")
    def test_downtimes_handles_flip_one_day_ago(self, mock_now):
        mock_now.return_value = datetime(2019, 7, 19, tzinfo=timezone.utc)

        check = Check.objects.create(project=self.project, status="down")
        flip = Flip(owner=check)
        flip.created = datetime(2019, 7, 18, tzinfo=timezone.utc)
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        r = check.downtimes(10)
        self.assertEqual(len(r), 10)
        for dt, downtime, outages in r:
            if dt.month == 7:
                self.assertEqual(downtime.total_seconds(), 86400)
                self.assertEqual(outages, 1)
            else:
                self.assertEqual(downtime.total_seconds(), 0)
                self.assertEqual(outages, 0)

    @patch("hc.api.models.timezone.now")
    def test_downtimes_handles_flip_two_months_ago(self, mock_now):
        mock_now.return_value = datetime(2019, 7, 19, tzinfo=timezone.utc)

        check = Check.objects.create(project=self.project, status="down")
        flip = Flip(owner=check)
        flip.created = datetime(2019, 5, 19, tzinfo=timezone.utc)
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        r = check.downtimes(10)
        self.assertEqual(len(r), 10)
        for dt, downtime, outages in r:
            if dt.month == 7:
                self.assertEqual(outages, 1)
            elif dt.month == 6:
                self.assertEqual(downtime.total_seconds(), 30 * 86400)
                self.assertEqual(outages, 1)
            elif dt.month == 5:
                self.assertEqual(outages, 1)
            else:
                self.assertEqual(downtime.total_seconds(), 0)
                self.assertEqual(outages, 0)
