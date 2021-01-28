# coding: utf-8

from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification, TokenBucket
from hc.test import BaseTestCase


class NotifyTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "po"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.requests.request")
    def test_pushover(self, mock_post):
        self._setup_data("123|0")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertIn("DOWN", payload["title"])

    @patch("hc.api.transports.requests.request")
    def test_pushover_up_priority(self, mock_post):
        self._setup_data("123|0|2", status="up")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertIn("UP", payload["title"])
        self.assertEqual(payload["priority"], 2)
        self.assertIn("retry", payload)
        self.assertIn("expire", payload)

    @override_settings(SECRET_KEY="test-secret")
    @patch("hc.api.transports.requests.request")
    def test_it_obeys_rate_limit(self, mock_post):
        self._setup_data("123|0")

        # "c0ca..." is sha1("123test-secret")
        obj = TokenBucket(value="po-c0ca2a9774952af32cabf86453f69e442c4ed0eb")
        obj.tokens = 0
        obj.save()

        self.channel.notify(self.check)
        n = Notification.objects.first()
        self.assertEqual(n.error, "Rate limit exceeded")
