# coding: utf-8

from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification, TokenBucket
from hc.test import BaseTestCase

API = "https://api.pushover.net/1"


class NotifyPushoverTestCase(BaseTestCase):
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
    def test_it_works(self, mock_post):
        self._setup_data("123|0")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        args, kwargs = mock_post.call_args
        self.assertEqual(args[1], API + "/messages.json")

        payload = kwargs["data"]
        self.assertIn("DOWN", payload["title"])
        self.assertEqual(payload["tags"], self.check.unique_key)

    @patch("hc.api.transports.requests.request")
    def test_it_supports_up_priority(self, mock_post):
        self._setup_data("123|0|2", status="up")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

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

    @patch("hc.api.transports.requests.request")
    def test_it_cancels_emergency_notification(self, mock_post):
        self._setup_data("123|2|0", status="up")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        self.assertEqual(mock_post.call_count, 2)

        cancel_args, cancel_kwargs = mock_post.call_args_list[0]
        expected = "/receipts/cancel_by_tag/%s.json" % self.check.unique_key
        self.assertEqual(cancel_args[1], API + expected)

        up_args, up_kwargs = mock_post.call_args_list[1]
        payload = up_kwargs["data"]
        self.assertIn("UP", payload["title"])
