from __future__ import annotations

import json
from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification, Ping
from hc.test import BaseTestCase


class LogTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        self.ping = Ping.objects.create(owner=self.check, n=1)
        self.ping.body_raw = b"hello world"

        # Older MySQL versions don't store microseconds. This makes sure
        # the ping is older than any notifications we may create later:
        self.ping.created = "2000-01-01T00:00:00+00:00"
        self.ping.save()

        self.url = f"/checks/{self.check.code}/log/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Browser's time zone", status_code=200)
        self.assertContains(r, "Found 1 ping event.")
        self.assertContains(r, "hello world")

    def test_it_displays_body(self) -> None:
        self.ping.body = "hello world"
        self.ping.body_raw = None
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Browser's time zone", status_code=200)
        self.assertContains(r, "hello world")

    @patch("hc.api.models.get_object")
    def test_it_does_not_load_body_from_object_storage(self, get_object: Mock) -> None:
        self.ping.body_raw = None
        self.ping.object_size = 1234
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "1234 byte body")
        get_object.assert_not_called()

    def test_it_displays_email(self) -> None:
        self.ping.scheme = "email"
        self.ping.ua = "email from server@example.org"
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "email from server@example.org", status_code=200)

    def test_team_access_works(self) -> None:
        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_bad_uuid(self) -> None:
        url = "/checks/not-uuid/log/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self) -> None:
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/log/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_checks_ownership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_email_notification(self) -> None:
        ch = Channel(kind="email", project=self.project)
        ch.value = json.dumps({"value": "alice@example.org", "up": True, "down": True})
        ch.save()

        Notification(owner=self.check, channel=ch, check_status="down").save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Sent email to alice@example.org", status_code=200)

    def test_it_shows_pushover_notification(self) -> None:
        ch = Channel.objects.create(kind="po", project=self.project)

        Notification(owner=self.check, channel=ch, check_status="down").save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Sent a Pushover notification", status_code=200)

    def test_it_shows_webhook_notification(self) -> None:
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

    def test_it_shows_ignored_nonzero_exitstatus(self) -> None:
        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Ignored", status_code=200)

    def test_it_handles_log_event(self) -> None:
        self.ping.kind = "log"
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "label-log", status_code=200)

    def test_it_does_not_show_duration_for_log_event(self) -> None:
        h = td(hours=1)
        Ping.objects.create(owner=self.check, n=2, kind="start", created=now() - h)
        Ping.objects.create(owner=self.check, n=3, kind="log", created=now() - h * 2)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "label-log", status_code=200)
        self.assertNotContains(r, "ic-timer", status_code=200)

    def test_it_does_not_show_duration_for_ign_event(self) -> None:
        h = td(hours=1)
        Ping.objects.create(owner=self.check, n=2, kind="start", created=now() - h)
        Ping.objects.create(owner=self.check, n=3, kind="ign", created=now() - h * 2)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "label-ign", status_code=200)
        self.assertNotContains(r, "ic-timer", status_code=200)

    def test_it_does_not_show_too_old_notifications(self) -> None:
        self.ping.created = now()
        self.ping.save()

        ch = Channel(kind="email", project=self.project)
        ch.value = json.dumps({"value": "alice@example.org", "up": True, "down": True})
        ch.save()

        n = Notification(owner=self.check)
        n.created = self.ping.created - td(hours=1)
        n.channel = ch
        n.check_status = "down"
        n.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        # The notification should not show up in the log as it is
        # older than the oldest visible ping:
        self.assertNotContains(r, "Sent email to alice@example.org", status_code=200)

    def test_it_accepts_start_query_parameter(self) -> None:
        dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
        ts = str(dt.timestamp())

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?start=" + ts)
        self.assertContains(r, f'data-start="{ts}"', status_code=200)

    def test_it_accepts_end_query_parameter(self) -> None:
        dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
        ts = str(dt.timestamp())

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?end=" + ts)
        self.assertContains(r, f'data-end="{ts}"', status_code=200)

    def test_it_ignores_bad_time_filter(self) -> None:
        self.ping.refresh_from_db()
        smin = str(self.ping.created.timestamp())

        for sample in ["surprise", "0"]:
            self.client.login(username="alice@example.org", password="password")
            r = self.client.get(self.url + "?start=" + sample)
            self.assertContains(r, f'data-start="{smin}"', status_code=200)
