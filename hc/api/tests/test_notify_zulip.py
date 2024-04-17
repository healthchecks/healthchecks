# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyZulipTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foobar"
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
        self.channel.kind = "zulip"
        self.channel.value = json.dumps(self.definition())
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"

    def definition(self, **kwargs: str) -> dict[str, str]:
        d = {
            "bot_email": "bot@example.org",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "general",
        }
        d.update(kwargs)
        return d

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        method, url = mock_post.call_args.args
        self.assertEqual(url, "https://example.org/api/v1/messages")

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["topic"], "Foobar is DOWN")
        self.assertIn("is **DOWN**.", payload["content"])
        self.assertIn("Last ping was 10 minutes ago.", payload["content"])

        # payload should not contain check's code
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.check.code), serialized)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_uses_custom_topic(self, mock_post: Mock) -> None:
        self.channel.value = json.dumps(self.definition(topic="foo"))
        self.channel.save()

        mock_post.return_value.status_code = 200
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["topic"], "foo")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_returns_error(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 403
        mock_post.return_value.content = b"""{"msg": "Nice try"}"""

        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, 'Received status code 403 with a message: "Nice try"')

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_non_json_error_response(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 403
        mock_post.return_value.json = Mock(side_effect=ValueError)

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 403")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_uses_site_parameter(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        definition = {
            "bot_email": "bot@example.org",
            "site": "https://custom.example.org",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "general",
        }
        self.channel.value = json.dumps(definition)

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        method, url = mock_post.call_args.args
        self.assertEqual(url, "https://custom.example.org/api/v1/messages")

        payload = mock_post.call_args.kwargs["data"]
        self.assertIn("DOWN", payload["topic"])

    @override_settings(ZULIP_ENABLED=False)
    def test_it_requires_zulip_enabled(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Zulip notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_escape_topic(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["topic"], "Foo & Bar is DOWN")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.ping.delete()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertNotIn("Last ping was", payload["content"])
