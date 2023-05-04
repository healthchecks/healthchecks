# coding: utf-8

from __future__ import annotations

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
        self.check.name = "Foo"
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "po"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        self._setup_data("123|0")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        url = mock_post.call_args.args[1]
        self.assertEqual(url, API + "/messages.json")

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["title"], "Foo is DOWN")
        self.assertIn(self.check.cloaked_url(), payload["message"])
        # Only one check in the project, so there should be no note about
        # other checks:
        self.assertNotIn("All the other checks are up.", payload["message"])
        self.assertEqual(payload["tags"], self.check.unique_key)

    @patch("hc.api.transports.curl.request")
    def test_it_supports_up_priority(self, mock_post):
        self._setup_data("123|0|2", status="up")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 1)

        payload = mock_post.call_args.kwargs["data"]
        self.assertIn("UP", payload["title"])
        self.assertEqual(payload["priority"], 2)
        self.assertIn("retry", payload)
        self.assertIn("expire", payload)

    @override_settings(SECRET_KEY="test-secret")
    @patch("hc.api.transports.curl.request")
    def test_it_obeys_rate_limit(self, mock_post):
        self._setup_data("123|0")

        # "c0ca..." is sha1("123test-secret")
        obj = TokenBucket(value="po-c0ca2a9774952af32cabf86453f69e442c4ed0eb")
        obj.tokens = 0
        obj.save()

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Rate limit exceeded")

    @patch("hc.api.transports.curl.request")
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

    @patch("hc.api.transports.curl.request")
    def test_it_shows_all_other_checks_up_note(self, mock_post):
        self._setup_data("123|0")
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "up"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertIn("All the other checks are up.", payload["message"])

    @patch("hc.api.transports.curl.request")
    def test_it_lists_other_down_checks(self, mock_post):
        self._setup_data("123|0")
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "down"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertIn("The following checks are also down", payload["message"])
        self.assertIn("Foobar", payload["message"])
        self.assertIn(other.cloaked_url(), payload["message"])

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_show_more_than_10_other_checks(self, mock_post):
        self._setup_data("123|0")
        mock_post.return_value.status_code = 200

        for i in range(0, 11):
            other = Check(project=self.project)
            other.name = f"Foobar #{i}"
            other.status = "down"
            other.last_ping = now() - td(minutes=61)
            other.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertNotIn("Foobar", payload["message"])
        self.assertIn("11 other checks are also down.", payload["message"])

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_escape_title(self, mock_post):
        self._setup_data("123|0")
        self.check.name = "Foo & Bar"
        self.check.save()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["title"], "Foo & Bar is DOWN")

    @patch("hc.api.transports.curl.request")
    def test_it_handles_disabled_priority(self, mock_post):
        self._setup_data("123|-3")

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 0)
        mock_post.assert_not_called()

    @patch("hc.api.transports.curl.request")
    def test_it_handles_disabled_up_priority(self, mock_post):
        self._setup_data("123|0|-3", status="up")

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 0)
        mock_post.assert_not_called()
