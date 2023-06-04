# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification, Ping
from hc.lib.curl import CurlError
from hc.test import BaseTestCase


class NotifySlackTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.name = "Foobar"
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=61)
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "slack"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @override_settings(SITE_ROOT="http://testserver", SITE_LOGO_URL=None)
    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        self._setup_data("https://example.org")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "https://example.org")

        payload = mock_post.call_args.kwargs["json"]
        attachment = payload["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Success, an hour ago")
        self.assertNotIn("Last Ping Body", fields)

        # The payload should not contain check's code
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.check.code), serialized)
        self.assertIn("http://testserver/static/img/logo.png", serialized)

    @patch("hc.api.transports.curl.request")
    def test_slack_with_complex_value(self, mock_post):
        v = json.dumps({"incoming_webhook": {"url": "123"}})
        self._setup_data(v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "123")

    @patch("hc.api.transports.curl.request")
    def test_it_handles_500(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 500

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 500")

    @patch("hc.api.transports.curl.request", side_effect=CurlError("Timed out"))
    def test_it_handles_timeout(self, mock_post):
        self._setup_data("123")

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Timed out")
        # Expect 1 try and 2 retries:
        self.assertEqual(mock_post.call_count, 3)

    @patch("hc.api.transports.curl.request")
    def test_slack_with_tabs_in_schedule(self, mock_post):
        self._setup_data("123")
        self.check.kind = "cron"
        self.check.schedule = "*\t* * * *"
        self.check.save()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)
        mock_post.assert_called_once()

    @override_settings(SLACK_ENABLED=False)
    def test_it_requires_slack_enabled(self):
        self._setup_data("123")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Slack notifications are not enabled.")

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_retry_404(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 404

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 404")
        self.assertEqual(mock_post.call_count, 1)

    @patch("hc.api.transports.curl.request")
    def test_it_disables_channel_on_404(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 404

        self.channel.notify(self.check)
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.disabled)

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request")
    def test_it_handles_last_ping_fail(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Failure, an hour ago")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request")
    def test_it_shows_nonzero_exit_status(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.check)
        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Exit status 123, an hour ago")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request")
    def test_it_handles_last_ping_log(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "log"
        self.ping.save()

        self.channel.notify(self.check)

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Log, an hour ago")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request")
    def test_it_shows_ignored_nonzero_exitstatus(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Ignored, an hour ago")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request")
    def test_it_shows_last_ping_body(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World"
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping Body"], "```\nHello World\n```")

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request")
    def test_it_shows_truncated_last_ping_body(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World" * 1000
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertIn("[truncated]", fields["Last Ping Body"])

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request")
    def test_it_skips_last_ping_body_containing_backticks(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello ``` World"
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertNotIn("Last Ping Body", fields)
