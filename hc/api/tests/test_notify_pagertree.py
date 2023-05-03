# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyPagertreeTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "pagertree"
        self.channel.value = "123"
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")

    @override_settings(PAGERTREE_ENABLED=False)
    def test_it_requires_pagertree_enabled(self):
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "PagerTree notifications are not enabled.")

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_escape_title(self, mock_post):
        mock_post.return_value.status_code = 200

        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "Foo & Bar is DOWN")
