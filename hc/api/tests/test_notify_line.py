# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification
from hc.test import BaseTestCase


class NotifyLineTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

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
        self.assertIn("Last ping was an hour ago.", params["message"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_escape_message(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.check.name = "Foo & Bar"
        self.check.status = "up"
        self.check.save()

        self.channel.notify(self.flip)

        params = mock_post.call_args.kwargs["params"]
        self.assertEqual(params["message"], 'The check "Foo & Bar" is now UP.')

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.check.last_ping = None
        self.check.save()

        mock_post.return_value.status_code = 200
        self.channel.notify(self.flip)

        params = mock_post.call_args.kwargs["params"]
        self.assertNotIn("Last ping was", params["message"])
