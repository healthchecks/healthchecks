
from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyDiscordTestCase(BaseTestCase):
    def _setup_data(self, url: str, status: str = "down") -> None:
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
        self.channel.kind = "discord"
        self.channel.value = json.dumps({"webhook": {"url": url}})
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        self._setup_data("https://example.org")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "https://example.org/slack")

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        self.assertEqual(attachment["fallback"], """The check "foo" is DOWN.""")

        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Success, 10 minutes ago")
        self.assertEqual(fields["Total Pings"], "112233")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_rewrites_discordapp_com(self, mock_post: Mock) -> None:
        self._setup_data("https://discordapp.com/foo")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        # discordapp.com is deprecated. For existing webhook URLs, we should
        # rewrite discordapp.com to discord.com:
        self.assertEqual(url, "https://discord.com/foo/slack")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_failure(self, mock_post: Mock) -> None:
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.save()

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Failure, 10 minutes ago")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_disables_channel_on_404(self, mock_post: Mock) -> None:
        self._setup_data("https://example.org")
        mock_post.return_value.status_code = 404

        self.channel.notify(self.flip)
        # Make sure the HTTP request was made only once (no retries):
        self.assertEqual(mock_post.call_count, 1)
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.disabled)
