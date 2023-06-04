# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification, Ping
from hc.test import BaseTestCase


class NotifyRocketChatTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=61)
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "rocketchat"
        self.channel.value = "https://example.org"
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "https://example.org")

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Success, an hour ago")

    @override_settings(ROCKETCHAT_ENABLED=False)
    def test_it_requires_rocketchat_enabled(self):
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Rocket.Chat notifications are not enabled.")

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_disable_channel_on_404(self, mock_post):
        mock_post.return_value.status_code = 404

        self.channel.notify(self.check)
        self.channel.refresh_from_db()
        self.assertFalse(self.channel.disabled)
        self.assertEqual(self.channel.last_error, "Received status code 404")

    @patch("hc.api.transports.curl.request")
    def test_it_shows_last_ping_body_size(self, mock_post):
        mock_post.return_value.status_code = 200

        self.ping.n = 123
        self.ping.body_raw = b"Hello World"
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertIn("11 bytes,", fields["Last Ping Body"])
        self.assertIn("#ping-123", fields["Last Ping Body"])

    @patch("hc.api.transports.curl.request")
    def test_it_shows_last_ping_body_one_byte(self, mock_post):
        mock_post.return_value.status_code = 200

        self.ping.n = 123
        self.ping.body_raw = b"X"
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertIn("1 byte,", fields["Last Ping Body"])

    @patch("hc.api.transports.curl.request")
    def test_it_shows_ping_kind_fail(self, mock_post):
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual("Failure, an hour ago", fields["Last Ping"])

    @patch("hc.api.transports.curl.request")
    def test_it_shows_nonzero_exitstatus(self, mock_post):
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual("Exit status 123, an hour ago", fields["Last Ping"])

    @patch("hc.api.transports.curl.request")
    def test_it_shows_ignored_nonzero_exitstatus(self, mock_post):
        mock_post.return_value.status_code = 200

        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual("Ignored, an hour ago", fields["Last Ping"])
