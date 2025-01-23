from __future__ import annotations

import json
from datetime import timedelta as td
from typing import Any
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyMsTeamsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
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
        self.channel.kind = "msteamsw"
        self.channel.value = "http://example.com/webhook"
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"
        self.flip.reason = "timeout"

    def facts(self, payload: Any) -> dict[str, str]:
        card = payload["attachments"][0]["content"]
        factset = card["body"][1]
        return {f["title"]: f["value"] for f in factset["facts"]}

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["type"], "message")

        card = payload["attachments"][0]["content"]
        # summary and title should be the same, except
        # title should have any special HTML characters escaped
        self.assertEqual(card["fallbackText"], "“Foo” is DOWN.")

        heading = card["body"][0]
        self.assertEqual(
            heading["text"],
            "🔴 “Foo” is DOWN (success signal did not"
            " arrive on time, grace time passed).",
        )

        facts = self.facts(payload)
        self.assertEqual(facts["Last Ping:"], "Success, 10 minutes ago")
        self.assertEqual(facts["Total Pings:"], "112233")

        # The payload should not contain check's code
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.check.code), serialized)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_reason_fail(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.flip.reason = "fail"
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        text = payload["attachments"][0]["content"]["body"][0]["text"]
        self.assertEqual(text, "🔴 “Foo” is DOWN (received a failure signal).")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_escapes_special_characters(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.name = "_underscores_ & more"
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["attachments"][0]["content"]
        self.assertEqual(card["fallbackText"], "“_underscores_ &amp; more” is DOWN.")
        heading = card["body"][0]
        self.assertIn("🔴 “_underscores_ &amp; more” is DOWN", heading["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_cron_schedule_and_tz(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.check.kind = "cron"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        facts = self.facts(payload)
        self.assertEqual(facts["Schedule:"], "\u034f* \u034f* \u034f* \u034f* \u034f*")
        self.assertEqual(facts["Time Zone:"], "Europe/Riga")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_oncalendar_schedule_and_tz(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.check.kind = "oncalendar"
        self.check.schedule = "Mon 2-29"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        facts = self.facts(payload)
        self.assertEqual(facts["Schedule:"], "Mon 2-29")
        self.assertEqual(facts["Time Zone:"], "Europe/Riga")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_escapes_stars_in_schedule(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.kind = "cron"
        self.check.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        facts = self.facts(payload)
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
        facts = self.facts(payload)
        self.assertEqual(facts["Last Ping:"], "Failure, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_log(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "log"
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        facts = self.facts(payload)
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
        facts = self.facts(payload)
        self.assertEqual(facts["Last Ping:"], "Ignored, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_last_ping_body(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World"
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        blocks = payload["attachments"][0]["content"]["body"]
        self.assertEqual(blocks[-1]["type"], "CodeBlock")
        self.assertEqual(blocks[-1]["codeSnippet"], "Hello World")
