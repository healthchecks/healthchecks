# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyGotidyTestCase(BaseTestCase):
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
        self.channel.kind = "gotify"
        self.channel.value = json.dumps({"url": "https://example.org", "token": "abc"})
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
        self.assertEqual(url, "https://example.org/message?token=abc")

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "Foo is DOWN")
        self.assertIn(self.check.cloaked_url(), payload["message"])
        self.assertIn("Last ping was 10 minutes ago.", payload["message"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_subpath(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.channel.value = json.dumps(
            {"url": "https://example.org/sub/", "token": "abc"}
        )

        self.channel.notify(self.flip)

        method, url = mock_post.call_args.args
        self.assertEqual(url, "https://example.org/sub/message?token=abc")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_subpath_with_missing_slash(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.channel.value = json.dumps(
            {"url": "https://example.org/sub", "token": "abc"}
        )

        self.channel.notify(self.flip)

        method, url = mock_post.call_args.args
        self.assertEqual(url, "https://example.org/sub/message?token=abc")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_all_other_checks_up_note(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "up"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("All the other checks are up.", payload["message"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_lists_other_down_checks(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "down"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("The following checks are also down", payload["message"])
        self.assertIn("Foobar", payload["message"])
        self.assertIn("(last ping: an hour ago)", payload["message"])
        self.assertIn(other.cloaked_url(), payload["message"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_other_checks_with_no_last_ping(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        Check.objects.create(project=self.project, status="down")

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("(last ping: never)", payload["message"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_show_more_than_10_other_checks(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        for i in range(0, 11):
            other = Check(project=self.project)
            other.name = f"Foobar #{i}"
            other.status = "down"
            other.last_ping = now() - td(minutes=61)
            other.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Foobar", payload["message"])
        self.assertIn("11 other checks are also down.", payload["message"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.ping.delete()

        mock_post.return_value.status_code = 200
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Last ping was", payload["message"])
