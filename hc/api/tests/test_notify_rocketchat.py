# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyRocketChatTestCase(BaseTestCase):
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
        self.channel.kind = "rocketchat"
        self.channel.value = "https://example.org"
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "https://example.org")

        text = mock_post.call_args.kwargs["json"]["text"]
        self.assertTrue(text.endswith("is DOWN."))

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Success, 10 minutes ago")
        self.assertEqual(fields["Total Pings"], "112233")

    @override_settings(ROCKETCHAT_ENABLED=False)
    def test_it_requires_rocketchat_enabled(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Rocket.Chat notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_disable_channel_on_404(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 404

        self.channel.notify(self.flip)
        self.channel.refresh_from_db()
        self.assertFalse(self.channel.disabled)
        self.assertEqual(self.channel.last_error, "Received status code 404")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_schedule_and_tz(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.check.kind = "cron"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)
        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Schedule"], "\u034f* \u034f* \u034f* \u034f* \u034f*")
        self.assertEqual(fields["Time Zone"], "Europe/Riga")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_last_ping_body_size(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.n = 123
        self.ping.body_raw = b"Hello World"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertIn("11 bytes,", fields["Last Ping Body"])
        self.assertIn("#ping-123", fields["Last Ping Body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_last_ping_body_one_byte(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.n = 123
        self.ping.body_raw = b"X"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertIn("1 byte,", fields["Last Ping Body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_ping_kind_fail(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual("Failure, 10 minutes ago", fields["Last Ping"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_nonzero_exitstatus(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual("Exit status 123, 10 minutes ago", fields["Last Ping"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_ignored_nonzero_exitstatus(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual("Ignored, 10 minutes ago", fields["Last Ping"])
