# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyLineTestCase(BaseTestCase):
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
        self.channel.kind = "linenotify"
        self.channel.value = "fake-token"
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

        headers = mock_post.call_args.kwargs["headers"]
        params = mock_post.call_args.kwargs["params"]
        self.assertEqual(headers["Authorization"], "Bearer fake-token")
        self.assertIn("""The check "Foo" is DOWN""", params["message"])
        self.assertIn("Last ping was 10 minutes ago.", params["message"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_escape_message(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.check.name = "Foo & Bar"
        self.check.save()

        self.flip.old_status = "down"
        self.flip.new_status = "up"

        self.channel.notify(self.flip)

        params = mock_post.call_args.kwargs["params"]
        self.assertEqual(params["message"], 'The check "Foo & Bar" is now UP.')

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.ping.delete()

        mock_post.return_value.status_code = 200
        self.channel.notify(self.flip)

        params = mock_post.call_args.kwargs["params"]
        self.assertNotIn("Last ping was", params["message"])
