# coding: utf-8

from datetime import timedelta as td
from unittest.mock import patch

from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase
from django.test.utils import override_settings


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

    @patch("hc.api.transports.requests.request")
    def test_pagertree(self, mock_post):
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")

    @override_settings(PAGERTREE_ENABLED=False)
    def test_it_requires_pagertree_enabled(self):
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "PagerTree notifications are not enabled.")
