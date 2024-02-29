# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch
from urllib.parse import quote

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


@override_settings(
    MATRIX_HOMESERVER="https://example.net", MATRIX_ACCESS_TOKEN="test-token"
)
class NotifyMatrixTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "matrix"
        self.channel.value = "!foo:example.org"
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        method, url = mock_post.call_args.args
        self.assertIn("https://example.net", url)
        self.assertIn(quote("!foo:example.org"), url)
        self.assertIn("test-token", url)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("Foo is DOWN.", payload["body"])
        self.assertIn("Last ping was an hour ago.", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.check.last_ping = None
        self.check.save()

        mock_post.return_value.status_code = 200
        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Last ping was", payload["body"])
