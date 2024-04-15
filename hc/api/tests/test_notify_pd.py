# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyPdTestCase(BaseTestCase):
    def _setup_data(
        self, value: str, status: str = "down", email_verified: bool = True
    ) -> None:
        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.desc = "Description goes here"
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=10)
        self.ping.n = 112233
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "pd"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["description"], "Foo is DOWN")
        self.assertEqual(payload["details"]["Description"], "Description goes here")
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "123")
        self.assertEqual(payload["details"]["Last ping"], "10 minutes ago")
        self.assertEqual(payload["details"]["Total pings"], 112233)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_schedule_and_tz(self, mock_post: Mock) -> None:
        self._setup_data("123")
        self.check.kind = "cron"
        self.check.tz = "Europe/Riga"
        self.check.save()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["details"]["Schedule"], "* * * * *")
        self.assertEqual(payload["details"]["Time zone"], "Europe/Riga")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_pd_complex(self, mock_post: Mock) -> None:
        self._setup_data(json.dumps({"service_key": "456"}))
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "456")

    @override_settings(PD_ENABLED=False)
    def test_it_requires_pd_enabled(self) -> None:
        self._setup_data("123")
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "PagerDuty notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_escape_description(self, mock_post: Mock) -> None:
        self._setup_data("123")
        self.check.name = "Foo & Bar"
        self.check.save()

        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["description"], "Foo & Bar is DOWN")
