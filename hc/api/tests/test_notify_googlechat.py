from __future__ import annotations

import json
from datetime import timedelta as td
from typing import Any
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now
from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.lib.curl import CurlError
from hc.lib.typealias import JSONValue
from hc.test import BaseTestCase


@patch("hc.api.transports.close_old_connections", Mock())
class NotifyGoogleChatTestCase(BaseTestCase):
    def _setup_data(self, status: str = "down", email_verified: bool = True) -> None:
        self.check = Check(project=self.project)
        self.check.name = "Foobar"
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
        self.channel.kind = "googlechat"
        self.channel.value = "https://example.org"
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status
        self.flip.reason = "timeout"

    def fields(self, doc: Any) -> dict[str, str]:
        result = {}
        widgets = doc["cardsV2"][0]["card"]["sections"]["widgets"]
        for w in widgets:
            if para := w.get("textParagraph"):
                result["text"] = para["text"]
            if dt := w.get("decoratedText"):
                result[dt["topLabel"]] = dt["text"]
            if buttons := w.get("buttonList"):
                result["url"] = buttons["buttons"][0]["onClick"]["openLink"]["url"]
        return result

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        self._setup_data()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "https://example.org")

        payload = mock_post.call_args.kwargs["json"]
        fields = self.fields(payload)
        self.assertIn("Reason: success signal did not arrive on time", fields["text"])
        self.assertEqual(fields["Last Ping"], "Success, 10 minutes ago")
        self.assertEqual(fields["Total Pings"], "112233")
        self.assertTrue(fields["url"].startswith("http://testserver/cloaked/"))

        # The payload should not contain check's code
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.check.code), serialized)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_reason_failure(self, mock_post: Mock) -> None:
        self._setup_data()
        mock_post.return_value.status_code = 200

        self.flip.reason = "fail"
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        fields = self.fields(payload)
        self.assertIn("Reason: received a failure signal.", fields["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_500(self, mock_post: Mock) -> None:
        self._setup_data()
        mock_post.return_value.status_code = 500

        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 500")

    @patch(
        "hc.api.transports.curl.request",
        autospec=True,
        side_effect=CurlError("Timed out"),
    )
    def test_it_handles_timeout(self, mock_post: Mock) -> None:
        self._setup_data()

        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Timed out")
        # Expect 1 try and 2 retries:
        self.assertEqual(mock_post.call_count, 3)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_cron_schedule_and_tz(self, mock_post: Mock) -> None:
        self._setup_data()
        self.check.kind = "cron"
        self.check.tz = "Europe/Riga"
        self.check.save()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        fields = self.fields(payload)
        self.assertEqual(fields["Schedule"], "* * * * *")
        self.assertEqual(fields["Time Zone"], "Europe/Riga")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_oncalendar_schedule_and_tz(self, mock_post: Mock) -> None:
        self._setup_data()
        self.check.kind = "oncalendar"
        self.check.schedule = "Mon 2-29"
        self.check.tz = "Europe/Riga"
        self.check.save()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        fields = self.fields(payload)
        self.assertEqual(fields["Schedule"], "Mon 2-29")
        self.assertEqual(fields["Time Zone"], "Europe/Riga")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_fail(self, mock_post: Mock) -> None:
        self._setup_data()
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        fields = self.fields(payload)
        self.assertEqual(fields["Last Ping"], "Failure, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_nonzero_exit_status(self, mock_post: Mock) -> None:
        self._setup_data()
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        fields = self.fields(payload)
        self.assertEqual(fields["Last Ping"], "Exit status 123, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_log(self, mock_post: Mock) -> None:
        self._setup_data()
        mock_post.return_value.status_code = 200

        self.ping.kind = "log"
        self.ping.save()

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        fields = self.fields(payload)
        self.assertEqual(fields["Last Ping"], "Log, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_ignored_nonzero_exitstatus(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        fields = self.fields(payload)
        self.assertEqual(fields["Last Ping"], "Ignored, 10 minutes ago")
