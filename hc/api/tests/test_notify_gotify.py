# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyGotidyTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "gotify"
        self.channel.value = json.dumps({"url": "https://example.org", "token": "abc"})
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "Foo is DOWN")
        self.assertIn(self.check.cloaked_url(), payload["message"])

    @patch("hc.api.transports.curl.request")
    def test_it_shows_all_other_checks_up_note(self, mock_post):
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "up"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("All the other checks are up.", payload["message"])

    @patch("hc.api.transports.curl.request")
    def test_it_lists_other_down_checks(self, mock_post):
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "down"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("The following checks are also down", payload["message"])
        self.assertIn("Foobar", payload["message"])
        self.assertIn(other.cloaked_url(), payload["message"])

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_show_more_than_10_other_checks(self, mock_post):
        mock_post.return_value.status_code = 200

        for i in range(0, 11):
            other = Check(project=self.project)
            other.name = f"Foobar #{i}"
            other.status = "down"
            other.last_ping = now() - td(minutes=61)
            other.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Foobar", payload["message"])
        self.assertIn("11 other checks are also down.", payload["message"])
