# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyOpsgenieTestCase(BaseTestCase):
    def _setup_data(
        self, value: str, status: str = "down", email_verified: bool = True
    ) -> None:
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
        self.channel.kind = "opsgenie"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        self._setup_data(json.dumps({"key": "123", "region": "us"}))
        mock_post.return_value.status_code = 202

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("""The check "Foo" is DOWN.""", payload["message"])
        self.assertIn("""The check "Foo" is DOWN.""", payload["description"])
        self.assertIn("Last ping was 10 minutes ago.", payload["description"])
        self.assertIn("Last ping was 10 minutes ago.", payload["note"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_opsgenie_with_legacy_value(self, mock_post: Mock) -> None:
        self._setup_data(json.dumps({"key": "123", "region": "us"}))
        mock_post.return_value.status_code = 202

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        self.assertEqual(mock_post.call_count, 1)
        url = mock_post.call_args.args[1]
        self.assertIn("api.opsgenie.com", url)
        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("DOWN", payload["message"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_opsgenie_up(self, mock_post: Mock) -> None:
        self._setup_data(json.dumps({"key": "123", "region": "us"}), status="up")
        mock_post.return_value.status_code = 202

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        self.assertEqual(mock_post.call_count, 1)
        method, url = mock_post.call_args.args
        self.assertTrue(str(self.check.code) in url)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_opsgenie_with_eu_region(self, mock_post: Mock) -> None:
        self._setup_data(json.dumps({"key": "456", "region": "eu"}))
        mock_post.return_value.status_code = 202

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        self.assertEqual(mock_post.call_count, 1)
        url = mock_post.call_args.args[1]
        self.assertIn("api.eu.opsgenie.com", url)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_opsgenie_returns_error(self, mock_post: Mock) -> None:
        self._setup_data(json.dumps({"key": "123", "region": "us"}))
        mock_post.return_value.status_code = 403
        mock_post.return_value.content = b"""{"message": "Nice try"}"""

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, 'Received status code 403 with a message: "Nice try"')

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_non_json_error_response(self, mock_post: Mock) -> None:
        self._setup_data(json.dumps({"key": "123", "region": "us"}))
        mock_post.return_value.status_code = 403
        mock_post.return_value.json = Mock(side_effect=ValueError)

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 403")

    @override_settings(OPSGENIE_ENABLED=False)
    def test_it_requires_opsgenie_enabled(self) -> None:
        self._setup_data(json.dumps({"key": "123", "region": "us"}))
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Opsgenie notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self._setup_data(json.dumps({"key": "123", "region": "us"}))
        self.ping.delete()
        mock_post.return_value.status_code = 202

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Last ping was", payload["description"])
        self.assertNotIn("Last ping was", payload["note"])
