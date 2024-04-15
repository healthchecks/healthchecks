# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifySpikeTestCase(BaseTestCase):
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
        self.channel.kind = "spike"
        self.channel.value = "https://spike.example.org"
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

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["check_id"], str(self.check.code))
        self.assertEqual(payload["title"], "Foo is DOWN")
        self.assertIn("Foo is DOWN.", payload["message"])
        self.assertIn("Last ping was 10 minutes ago.", payload["message"])

    @override_settings(SPIKE_ENABLED=False)
    def test_it_requires_spike_enabled(self) -> None:
        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Spike notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_escape(self, mock_post: Mock) -> None:
        self.check.name = "Foo & Bar"
        self.check.save()
        self.flip.new_status = "up"

        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "Foo & Bar is UP")
        self.assertEqual(payload["message"], "Foo & Bar is UP.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.ping.delete()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Last ping was", payload["message"])
