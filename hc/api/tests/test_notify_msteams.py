# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyMsTeamsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
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
        self.channel.kind = "msteams"
        self.channel.value = "http://example.com/webhook"
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.name = "_underscores_ & more"

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["@type"], "MessageCard")

        # summary and title should be the same, except
        # title should have any special HTML characters escaped
        self.assertEqual(payload["summary"], "“_underscores_ & more” is DOWN.")
        self.assertEqual(payload["title"], "“_underscores_ &amp; more” is DOWN.")

        facts = {f["name"]: f["value"] for f in payload["sections"][0]["facts"]}
        self.assertEqual(facts["Last Ping:"], "Success, 10 minutes ago")
        self.assertEqual(facts["Total Pings:"], "112233")

        # The payload should not contain check's code
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.check.code), serialized)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_schedule_and_tz(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.check.kind = "cron"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        facts = {f["name"]: f["value"] for f in payload["sections"][0]["facts"]}
        self.assertEqual(facts["Schedule:"], "\u034f* \u034f* \u034f* \u034f* \u034f*")
        self.assertEqual(facts["Time Zone:"], "Europe/Riga")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_escapes_stars_in_schedule(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.kind = "cron"
        self.check.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        facts = {f["name"]: f["value"] for f in payload["sections"][0]["facts"]}
        self.assertEqual(facts["Schedule:"], "\u034f* \u034f* \u034f* \u034f* \u034f*")

    @override_settings(MSTEAMS_ENABLED=False)
    def test_it_requires_msteams_enabled(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "MS Teams notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_fail(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        facts = {f["name"]: f["value"] for f in payload["sections"][0]["facts"]}
        self.assertEqual(facts["Last Ping:"], "Failure, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_log(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "log"
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        facts = {f["name"]: f["value"] for f in payload["sections"][0]["facts"]}
        self.assertEqual(facts["Last Ping:"], "Log, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_ignored_nonzero_exitstatus(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        facts = {f["name"]: f["value"] for f in payload["sections"][0]["facts"]}
        self.assertEqual(facts["Last Ping:"], "Ignored, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_last_ping_body(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        section = payload["sections"][-1]
        self.assertIn("```\nHello World\n```", section["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_truncated_last_ping_body(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World" * 1000
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        section = payload["sections"][-1]
        self.assertIn("[truncated]", section["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_skips_last_ping_body_with_backticks(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello ``` World"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        section = payload["sections"][-1]
        self.assertNotIn("Hello", section["text"])
