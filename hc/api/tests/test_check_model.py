from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import make_aware, now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase

CURRENT_TIME = datetime(2020, 1, 15, tzinfo=timezone.utc)
MOCK_NOW = Mock(return_value=CURRENT_TIME)


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
        check.last_ping = now() - td(days=1, minutes=30)

        self.assertEqual(check.get_status(), "grace")

    def test_get_status_handles_paused_check(self):
        check = Check()
        check.status = "paused"
        check.last_ping = now() - td(days=1, minutes=30)
        self.assertEqual(check.get_status(), "paused")

    def test_status_works_with_cron_syntax(self):
        dt = make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

        # Expect ping every midnight, default grace is 1 hour
        check = Check()
        check.kind = "cron"
        check.schedule = "0 0 * * *"
        check.status = "up"
        check.last_ping = dt

        with patch("hc.api.models.now") as mock_now:
            # 23:59pm
            mock_now.return_value = dt + td(hours=23, minutes=59)
            self.assertEqual(check.get_status(), "up")

        with patch("hc.api.models.now") as mock_now:
            # 00:00am
            mock_now.return_value = dt + td(days=1)
            self.assertEqual(check.get_status(), "grace")

        with patch("hc.api.models.now") as mock_now:
            # 1:30am
            mock_now.return_value = dt + td(days=1, minutes=60)
            self.assertEqual(check.get_status(), "down")

    def test_status_works_with_timezone(self):
        dt = make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

        # Expect ping every day at 10am, default grace is 1 hour
        check = Check()
        check.kind = "cron"
        check.schedule = "0 10 * * *"
        check.status = "up"
        check.last_ping = dt
        check.tz = "Australia/Brisbane"  # UTC+10

        with patch("hc.api.models.now") as mock_now:
            # 10:30am
            mock_now.return_value = dt + td(hours=23, minutes=59)
            self.assertEqual(check.get_status(), "up")

        with patch("hc.api.models.now") as mock_now:
            # 10:30am
            mock_now.return_value = dt + td(days=1)
            self.assertEqual(check.get_status(), "grace")

        with patch("hc.api.models.now") as mock_now:
            # 11:30am
            mock_now.return_value = dt + td(days=1, minutes=60)
            self.assertEqual(check.get_status(), "down")

    def test_get_status_handles_past_grace(self):
        check = Check()
        check.status = "up"
        check.last_ping = now() - td(days=2)

        self.assertEqual(check.get_status(), "down")

    def test_get_status_obeys_down_status(self):
        check = Check()
        check.status = "down"
        check.last_ping = now() - td(minutes=1)

        self.assertEqual(check.get_status(), "down")

    def test_get_status_handles_started(self):
        check = Check()
        check.last_ping = now() - td(hours=2)
        # Last start was 5 minutes ago, display status should be "started"
        check.last_start = now() - td(minutes=5)
        for status in ("new", "paused", "up", "down"):
            check.status = status
            self.assertEqual(check.get_status(with_started=True), "started")

    def test_get_status_handles_down_then_started_and_expired(self):
        check = Check(status="down")
        # Last ping was 2 days ago
        check.last_ping = now() - td(days=2)
        # Last start was 2 hours ago - the check is past its grace time
        check.last_start = now() - td(hours=2)

        self.assertEqual(check.get_status(with_started=True), "down")
        self.assertEqual(check.get_status(), "down")

    def test_get_status_handles_up_then_started(self):
        check = Check(status="up")
        # Last ping was 2 hours ago, so is still up
        check.last_ping = now() - td(hours=2)
        # Last start was 5 minutes ago
        check.last_start = now() - td(minutes=5)

        self.assertEqual(check.get_status(with_started=True), "started")
        # A started check still is considered "up":
        self.assertEqual(check.get_status(), "up")

    def test_get_status_handles_up_then_started_and_expired(self):
        check = Check(status="up")
        # Last ping was 3 hours ago, so is still up
        check.last_ping = now() - td(hours=3)
        # Last start was 2 hours ago - the check is past its grace time
        check.last_start = now() - td(hours=2)

        self.assertEqual(check.get_status(with_started=True), "down")
        self.assertEqual(check.get_status(), "down")

    def test_get_status_handles_paused_then_started_and_expired(self):
        check = Check(status="paused")
        # Last start was 2 hours ago - the check is past its grace time
        check.last_start = now() - td(hours=2)

        self.assertEqual(check.get_status(with_started=True), "down")
        self.assertEqual(check.get_status(), "down")

    def test_get_status_handles_started_and_mia(self):
        check = Check()
        check.last_start = now() - td(hours=2)

        self.assertEqual(check.get_status(with_started=True), "down")
        self.assertEqual(check.get_status(), "down")

    def test_next_ping_with_cron_syntax(self):
        dt = make_aware(datetime(2000, 1, 1), timezone=timezone.utc)

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

    @patch("hc.api.models.now", MOCK_NOW)
    @patch("hc.lib.date.now", MOCK_NOW)
    def test_downtimes_handles_no_flips(self):
        check = Check(project=self.project)
        check.created = datetime(2019, 1, 1, tzinfo=timezone.utc)
        check.save()

        nov, dec, jan = check.downtimes(3, "UTC")

        # Nov. 2019
        self.assertEqual(nov[0].strftime("%m-%Y"), "11-2019")
        self.assertEqual(nov[1], td())
        self.assertEqual(nov[2], 0)

        # Dec. 2019
        self.assertEqual(dec[0].strftime("%m-%Y"), "12-2019")
        self.assertEqual(dec[1], td())
        self.assertEqual(dec[2], 0)

        # Jan. 2020
        self.assertEqual(jan[0].strftime("%m-%Y"), "01-2020")
        self.assertEqual(jan[1], td())
        self.assertEqual(jan[2], 0)

    @patch("hc.api.models.now", MOCK_NOW)
    @patch("hc.lib.date.now", MOCK_NOW)
    def test_downtimes_handles_currently_down_check(self):
        check = Check(project=self.project, status="down")
        check.created = datetime(2019, 1, 1, tzinfo=timezone.utc)
        check.save()

        r = check.downtimes(10, "UTC")
        self.assertEqual(len(r), 10)
        for dt, downtime, outages in r:
            self.assertEqual(outages, 1)

    @patch("hc.api.models.now", MOCK_NOW)
    @patch("hc.lib.date.now", MOCK_NOW)
    def test_downtimes_handles_flip_one_day_ago(self):
        check = Check.objects.create(project=self.project, status="down")
        check.created = datetime(2019, 1, 1, tzinfo=timezone.utc)

        flip = Flip(owner=check)
        flip.created = datetime(2020, 1, 14, tzinfo=timezone.utc)
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        r = check.downtimes(10, "UTC")
        self.assertEqual(len(r), 10)
        for dt, downtime, outages in r:
            if dt.month == 1:
                self.assertEqual(downtime.total_seconds(), 86400)
                self.assertEqual(outages, 1)
            else:
                self.assertEqual(downtime.total_seconds(), 0)
                self.assertEqual(outages, 0)

    @patch("hc.api.models.now", MOCK_NOW)
    @patch("hc.lib.date.now", MOCK_NOW)
    def test_downtimes_handles_flip_two_months_ago(self):
        check = Check.objects.create(project=self.project, status="down")
        check.created = datetime(2019, 1, 1, tzinfo=timezone.utc)

        flip = Flip(owner=check)
        flip.created = datetime(2019, 11, 15, tzinfo=timezone.utc)
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        r = check.downtimes(3, "UTC")
        self.assertEqual(len(r), 3)

        dt, duration, outages = r[0]
        self.assertEqual(dt.isoformat(), "2019-11-01T00:00:00+00:00")
        self.assertEqual(duration, td(days=16))
        self.assertEqual(outages, 1)

        dt, duration, outages = r[1]
        self.assertEqual(dt.isoformat(), "2019-12-01T00:00:00+00:00")
        self.assertEqual(duration, td(days=31))
        self.assertEqual(outages, 1)

        dt, duration, outages = r[2]
        self.assertEqual(dt.isoformat(), "2020-01-01T00:00:00+00:00")
        self.assertEqual(duration, td(days=14))
        self.assertEqual(outages, 1)

    @patch("hc.api.models.now", MOCK_NOW)
    @patch("hc.lib.date.now", MOCK_NOW)
    def test_downtimes_handles_non_utc_timezone(self):
        check = Check.objects.create(project=self.project, status="down")
        check.created = datetime(2019, 1, 1, tzinfo=timezone.utc)

        flip = Flip(owner=check)
        flip.created = datetime(2019, 12, 31, 23, tzinfo=timezone.utc)
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        r = check.downtimes(2, "Europe/Riga")
        self.assertEqual(len(r), 2)

        dt, duration, outages = r[0]
        self.assertEqual(dt.isoformat(), "2019-12-01T00:00:00+02:00")
        self.assertEqual(duration, td())
        self.assertEqual(outages, 0)

        dt, duration, outages = r[1]
        self.assertEqual(dt.isoformat(), "2020-01-01T00:00:00+02:00")
        self.assertEqual(duration, td(days=14, hours=1))
        self.assertEqual(outages, 1)

    @patch("hc.api.models.now", MOCK_NOW)
    @patch("hc.lib.date.now", MOCK_NOW)
    def test_downtimes_handles_months_when_check_did_not_exist(self):
        check = Check(project=self.project)
        check.created = datetime(2020, 1, 1, 9, tzinfo=timezone.utc)
        check.save()

        nov, dec, jan = check.downtimes(3, "UTC")

        # Nov. 2019
        self.assertIsNone(nov[1])
        self.assertIsNone(nov[2])

        # Dec. 2019
        self.assertIsNone(dec[1])
        self.assertIsNone(dec[2])

        # Jan. 2020
        self.assertEqual(jan[1], td())
        self.assertEqual(jan[2], 0)

    @override_settings(S3_BUCKET=None)
    def test_it_prunes(self):
        check = Check.objects.create(project=self.project, n_pings=101)
        Ping.objects.create(owner=check, n=101)
        Ping.objects.create(owner=check, n=1)

        n = Notification(owner=check)
        n.channel = Channel.objects.create(project=self.project, kind="email")
        n.check_status = "down"
        n.created = check.created - td(minutes=10)
        n.save()

        check.prune()

        self.assertTrue(Ping.objects.filter(n=101).exists())
        self.assertFalse(Ping.objects.filter(n=1).exists())

        self.assertEqual(Notification.objects.count(), 0)

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.remove_objects")
    def test_it_prunes_object_storage(self, remove_objects):
        check = Check.objects.create(project=self.project, n_pings=101)
        Ping.objects.create(owner=check, n=101)
        Ping.objects.create(owner=check, n=1, object_size=1000)

        check.prune()
        code, upto_n = remove_objects.call_args.args
        self.assertEqual(code, check.code)
        self.assertEqual(upto_n, 1)
