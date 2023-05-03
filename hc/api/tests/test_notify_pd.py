# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyPdTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.desc = "Description goes here"
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "pd"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["description"], "Foo is DOWN")
        self.assertEqual(payload["details"]["Description"], "Description goes here")
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "123")

    @patch("hc.api.transports.curl.request")
    def test_pd_complex(self, mock_post):
        self._setup_data(json.dumps({"service_key": "456"}))
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "456")

    @override_settings(PD_ENABLED=False)
    def test_it_requires_pd_enabled(self):
        self._setup_data("123")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "PagerDuty notifications are not enabled.")

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_escape_description(self, mock_post):
        self._setup_data("123")
        self.check.name = "Foo & Bar"
        self.check.save()

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["description"], "Foo & Bar is DOWN")
