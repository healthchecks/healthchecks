# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch
from urllib.parse import quote

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


@override_settings(
    MATRIX_HOMESERVER="https://example.net", MATRIX_ACCESS_TOKEN="test-token"
)
class NotifyMatrixTestCase(BaseTestCase):
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
        self.channel.kind = "matrix"
        self.channel.value = "!foo:example.org"
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

        method, url = mock_post.call_args.args
        self.assertIn("https://example.net", url)
        self.assertIn(quote("!foo:example.org"), url)
        self.assertIn("test-token", url)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("Foo is DOWN.", payload["body"])
        self.assertIn("Last ping was 10 minutes ago.", payload["body"])
        self.assertIn("Last ping was 10 minutes ago.", payload["formatted_body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.ping.delete()

        mock_post.return_value.status_code = 200
        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Last ping was", payload["body"])
        self.assertNotIn("Last ping was", payload["formatted_body"])
