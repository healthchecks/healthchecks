from __future__ import annotations

import json
import uuid
from datetime import timedelta as td
from unittest.mock import patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification, Ping
from hc.test import BaseTestCase


class LogTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        self.ping = Ping.objects.create(owner=self.check, n=1)
        self.ping.body_raw = b"hello world"

        # Older MySQL versions don't store microseconds. This makes sure
        # the ping is older than any notifications we may create later:
        self.ping.created = "2000-01-01T00:00:00+00:00"
        self.ping.save()

        self.url = "/checks/%s/log/" % self.check.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Browser's time zone", status_code=200)
        self.assertContains(r, "Found 1 ping event.")
        self.assertContains(r, "hello world")

    def test_it_displays_body(self):
        self.ping.body = "hello world"
        self.ping.body_raw = None
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Browser's time zone", status_code=200)
        self.assertContains(r, "hello world")

    @patch("hc.api.models.get_object")
    def test_it_does_not_load_bodies_from_object_storage(self, get_object):
        self.ping.body_raw = None
        self.ping.object_size = 1234
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "1234 byte body")

        self.assertFalse(get_object.called)

    def test_it_displays_email(self):
        self.ping.scheme = "email"
        self.ping.ua = "email from server@example.org"
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "email from server@example.org", status_code=200)

    def test_team_access_works(self):

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/log/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/log/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_checks_ownership(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_email_notification(self):
        ch = Channel(kind="email", project=self.project)
        ch.value = json.dumps({"value": "alice@example.org", "up": True, "down": True})
        ch.save()

        Notification(owner=self.check, channel=ch, check_status="down").save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Sent email to alice@example.org", status_code=200)

    def test_it_shows_pushover_notification(self):
        ch = Channel.objects.create(kind="po", project=self.project)

        Notification(owner=self.check, channel=ch, check_status="down").save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Sent a Pushover notification", status_code=200)

    def test_it_shows_webhook_notification(self):
        ch = Channel(kind="webhook", project=self.project)
        ch.value = json.dumps(
            {
                "method_down": "GET",
                "url_down": "foo/$NAME",
                "body_down": "",
                "headers_down": {},
            }
        )
        ch.save()

        Notification(owner=self.check, channel=ch, check_status="down").save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Called webhook foo/$NAME", status_code=200)

    def test_it_allows_cross_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_shows_ignored_nonzero_exitstatus(self):
        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Ignored", status_code=200)

    def test_it_handles_log_event(self):
        self.ping.kind = "log"
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "label-log", status_code=200)

    def test_it_calculates_duration_with_overlapping_runs(self):
        # creates 3 overlapping runs according to the following timestamps:
        # ts 0: Cs
        # ts 1: As
        # ts 2: Bs
        # ts 3: Ae
        # ts 4: Ce
        # ts 6: Be
        # run A is 2 minutes long, B is 5 minutes and C is 4 minutes.

        uuid_a = str(uuid.uuid4())
        uuid_b = str(uuid.uuid4())
        uuid_c = None
        end_time_b = now()
        end_time_c = end_time_b - td(minutes=3)
        end_time_a = end_time_c - td(minutes=1)
        start_time_b = end_time_a - td(minutes=1)
        start_time_a = start_time_b - td(minutes=1)
        start_time_c = start_time_a - td(minutes=1)

        Ping.objects.create(owner=self.check, created=start_time_c, n=2, kind="start", rid=uuid_c)
        Ping.objects.create(owner=self.check, created=start_time_a, n=3, kind="start", rid=uuid_a)
        Ping.objects.create(owner=self.check, created=start_time_b, n=4, kind="start", rid=uuid_b)
        Ping.objects.create(owner=self.check, created=end_time_a, n=5, kind="", rid=uuid_a)
        Ping.objects.create(owner=self.check, created=end_time_c, n=6, kind="", rid=uuid_c)
        Ping.objects.create(owner=self.check, created=end_time_b, n=7, kind="", rid=uuid_b)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, "2 min 0 sec", status_code=200)
        self.assertContains(r, "5 min 0 sec", status_code=200)
        self.assertContains(r, "4 min 0 sec", status_code=200)

    def test_it_does_not_show_duration_for_log_event(self):
        h = td(hours=1)
        Ping.objects.create(owner=self.check, n=2, kind="start", created=now() - h)
        Ping.objects.create(owner=self.check, n=3, kind="log", created=now() - h * 2)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "label-log", status_code=200)
        self.assertNotContains(r, "ic-timer", status_code=200)

    def test_it_does_not_show_duration_for_ign_event(self):
        h = td(hours=1)
        Ping.objects.create(owner=self.check, n=2, kind="start", created=now() - h)
        Ping.objects.create(owner=self.check, n=3, kind="ign", created=now() - h * 2)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "label-ign", status_code=200)
        self.assertNotContains(r, "ic-timer", status_code=200)
