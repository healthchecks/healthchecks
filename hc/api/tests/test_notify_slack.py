# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.lib.curl import CurlError
from hc.test import BaseTestCase


class NotifySlackTestCase(BaseTestCase):
    def _setup_data(
        self, value: str, status: str = "down", email_verified: bool = True
    ) -> None:
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
        self.channel.kind = "slack"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status

    @override_settings(SITE_ROOT="http://testserver", SITE_LOGO_URL=None)
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        self._setup_data("https://example.org")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "https://example.org")

        payload = mock_post.call_args.kwargs["json"]
        attachment = payload["attachments"][0]
        self.assertEqual(attachment["fallback"], """The check "Foobar" is DOWN.""")

        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Success, 10 minutes ago")
        self.assertEqual(fields["Total Pings"], "112233")
        self.assertNotIn("Last Ping Body", fields)

        # The payload should not contain check's code
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.check.code), serialized)
        self.assertIn("http://testserver/static/img/logo.png", serialized)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_slack_with_complex_value(self, mock_post: Mock) -> None:
        v = json.dumps({"incoming_webhook": {"url": "123"}})
        self._setup_data(v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "123")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_500(self, mock_post: Mock) -> None:
        self._setup_data("123")
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
        self._setup_data("123")

        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Timed out")
        # Expect 1 try and 2 retries:
        self.assertEqual(mock_post.call_count, 3)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_schedule_and_tz(self, mock_post: Mock) -> None:
        self._setup_data("123")
        self.check.kind = "cron"
        self.check.tz = "Europe/Riga"
        self.check.save()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        payload = mock_post.call_args.kwargs["json"]
        attachment = payload["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Schedule"], "\u034f* \u034f* \u034f* \u034f* \u034f*")
        self.assertEqual(fields["Time Zone"], "Europe/Riga")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_slack_with_tabs_in_schedule(self, mock_post: Mock) -> None:
        self._setup_data("123")
        self.check.kind = "cron"
        self.check.schedule = "*\t* * * *"
        self.check.save()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        self.assertEqual(Notification.objects.count(), 1)
        mock_post.assert_called_once()

    @override_settings(SLACK_ENABLED=False)
    def test_it_requires_slack_enabled(self) -> None:
        self._setup_data("123")
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Slack notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_retry_404(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 404

        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 404")
        self.assertEqual(mock_post.call_count, 1)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_disables_channel_on_404(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 404

        self.channel.notify(self.flip)
        # Make sure the HTTP request was made only once (no retries):
        self.assertEqual(mock_post.call_count, 1)
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.disabled)

    @patch("hc.api.transports.logger.debug", autospec=True)
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_disables_channel_on_400_invalid_token(
        self, mock_post: Mock, debug: Mock
    ) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 400
        mock_post.return_value.content = b"invalid_token"

        self.channel.notify(self.flip)

        self.channel.refresh_from_db()
        self.assertTrue(self.channel.disabled)

        # It should give up after the first try
        self.assertEqual(mock_post.call_count, 1)
        # It should not log HTTP 400 "invalid_token" responses
        self.assertFalse(debug.called)

    @patch("hc.api.transports.logger.debug", autospec=True)
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_logs_unexpected_400(self, mock_post: Mock, debug: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 400
        mock_post.return_value.content = b"surprise"

        self.channel.notify(self.flip)
        self.assertTrue(debug.called)

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_fail(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Failure, 10 minutes ago")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_nonzero_exit_status(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)
        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Exit status 123, 10 minutes ago")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_log(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "log"
        self.ping.save()

        self.channel.notify(self.flip)

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Log, 10 minutes ago")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_ignored_nonzero_exitstatus(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Ignored, 10 minutes ago")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_last_ping_body(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping Body"], "```\nHello World\n```")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_truncated_last_ping_body(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World" * 1000
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertIn("[truncated]", fields["Last Ping Body"])

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_skips_last_ping_body_with_backticks(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello ``` World"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertNotIn("Last Ping Body", fields)
