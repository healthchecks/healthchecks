# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyMattermostTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "foo"
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
        self.channel.kind = "mattermost"
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

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        self.assertEqual(attachment["fallback"], """The check "foo" is DOWN.""")

        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Success, 10 minutes ago")
        self.assertEqual(fields["Total Pings"], "112233")

    @override_settings(MATTERMOST_ENABLED=False)
    def test_it_requires_mattermost_enabled(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Mattermost notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_disable_channel_on_404(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 404

        self.channel.notify(self.flip)
        self.channel.refresh_from_db()
        self.assertFalse(self.channel.disabled)

    @override_settings(SITE_ROOT="http://testserver")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_last_ping_body(self, mock_post: Mock) -> None:
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
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello ``` World"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertNotIn("Last Ping Body", fields)
