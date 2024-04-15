from __future__ import annotations

import json
from datetime import timedelta as td
from urllib.parse import urlencode

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class LogTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.check.created = "2000-01-01T00:00:00+00:00"
        self.check.save()

        ch = Channel(kind="email", project=self.project)
        ch.value = json.dumps({"value": "alice@example.org", "up": True, "down": True})
        ch.save()

        f = Flip(owner=self.check)
        f.created = now() - td(hours=1)
        f.old_status = "new"
        f.new_status = "down"
        f.save()

        n = Notification(owner=self.check)
        n.created = now() - td(hours=1)
        n.channel = ch
        n.check_status = "down"
        n.save()

        self.ping = Ping.objects.create(owner=self.check, n=1)
        self.ping.body_raw = b"hello world"
        # Older MySQL versions don't store microseconds. This makes sure
        # the ping is older than any notifications we may create later:
        self.ping.created = "2000-01-01T00:00:00+00:00"
        self.ping.save()

    def url(self, u: str | None = None, **kwargs: bool) -> str:
        params = {}
        for key in ("success", "fail", "start", "log", "ign", "notification", "flip"):
            if kwargs.get(key, True):
                params[key] = "on"
        if u:
            params["u"] = u

        return f"/checks/{self.check.code}/log_events/?" + urlencode(params)

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url())
        self.assertContains(r, "hello world", status_code=200)
        self.assertContains(r, "Sent email to alice@example.org")
        self.assertContains(r, "new ➔ down")

    def test_team_access_works(self) -> None:
        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)

    def test_it_handles_bad_uuid(self) -> None:
        url = "/checks/not-uuid/log_events/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self) -> None:
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/log_events/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_checks_ownership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 404)

    def test_it_accepts_start_parameter(self) -> None:
        ts = str(now().timestamp())
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url(u=ts))
        self.assertNotContains(r, "hello world")

    def test_it_rejects_bad_u_parameter(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        for sample in ["surprise", "100000000000000000"]:
            r = self.client.get(self.url(u=sample))
            self.assertEqual(r.status_code, 400)

    def test_it_does_not_show_too_old_notifications(self) -> None:
        # This moves ping #1 outside the 100 most recent pings:
        Ping.objects.create(owner=self.check, n=101)
        self.check.n_pings = 101
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url())

        # The notification should not show up in the log as it is
        # older than the oldest visible ping:
        self.assertNotContains(r, "Sent email to alice@example.org", status_code=200)

    def test_live_updates_do_not_return_too_old_notifications(self) -> None:
        # This moves ping #1 outside the 100 most recent pings:
        Ping.objects.create(owner=self.check, n=101)
        self.check.n_pings = 101
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url(u="1262296800"))

        # The notification should not show up in the log as it is
        # older than the oldest visible ping:
        self.assertNotContains(r, "Sent email to alice@example.org", status_code=200)

    def test_it_filters_success(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url(success=False))
        self.assertNotContains(r, "hello world")
        self.assertContains(r, "Sent email to alice@example.org", status_code=200)

    def test_it_filters_notification(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url(notification=False))
        self.assertContains(r, "hello world")
        self.assertNotContains(r, "Sent email to alice@example.org", status_code=200)

    def test_it_filters_flip(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url(flip=False))
        self.assertContains(r, "hello world")
        self.assertNotContains(r, "new ➔ down")

    def test_it_shows_email_notification(self) -> None:
        ch = Channel(kind="email", project=self.project)
        ch.value = json.dumps({"value": "alice@example.org", "up": True, "down": True})
        ch.save()

        Notification(owner=self.check, channel=ch, check_status="down").save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url())
        self.assertContains(r, "Sent email to alice@example.org", status_code=200)

    def test_it_shows_pushover_notification(self) -> None:
        ch = Channel.objects.create(kind="po", project=self.project)

        Notification(owner=self.check, channel=ch, check_status="down").save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url())
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
        r = self.client.get(self.url())
        self.assertContains(r, "Called webhook foo/$NAME", status_code=200)
