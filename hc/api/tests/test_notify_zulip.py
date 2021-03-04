# coding: utf-8

from datetime import timedelta as td
import json
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.name = "Foobar"
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "zulip"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.requests.request")
    def test_zulip(self, mock_post):
        definition = {
            "bot_email": "bot@example.org",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "general",
        }
        self._setup_data(json.dumps(definition))
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args

        method, url = args
        self.assertEqual(url, "https://example.org/api/v1/messages")

        payload = kwargs["data"]
        self.assertIn("DOWN", payload["topic"])

        # payload should not contain check's code
        serialized = json.dumps(payload)
        self.assertNotIn(str(self.check.code), serialized)

    @patch("hc.api.transports.requests.request")
    def test_zulip_returns_error(self, mock_post):
        definition = {
            "bot_email": "bot@example.org",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "general",
        }
        self._setup_data(json.dumps(definition))
        mock_post.return_value.status_code = 403
        mock_post.return_value.json.return_value = {"msg": "Nice try"}

        self.channel.notify(self.check)

        n = Notification.objects.first()
        self.assertEqual(n.error, 'Received status code 403 with a message: "Nice try"')

    @patch("hc.api.transports.requests.request")
    def test_zulip_uses_site_parameter(self, mock_post):
        definition = {
            "bot_email": "bot@example.org",
            "site": "https://custom.example.org",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "general",
        }
        self._setup_data(json.dumps(definition))
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args

        method, url = args
        self.assertEqual(url, "https://custom.example.org/api/v1/messages")

        payload = kwargs["data"]
        self.assertIn("DOWN", payload["topic"])

    @override_settings(ZULIP_ENABLED=False)
    def test_it_requires_zulip_enabled(self):
        definition = {
            "bot_email": "bot@example.org",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "general",
        }
        self._setup_data(json.dumps(definition))

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Zulip notifications are not enabled.")
