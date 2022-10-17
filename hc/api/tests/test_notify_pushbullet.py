# coding: utf-8

from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyPushbulletTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.status = "up"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "pushbullet"
        self.channel.value = "fake-token"
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["type"], "note")
        self.assertEqual(
            kwargs["json"]["body"], 'The check "Foo" received a ping and is now UP.'
        )
        self.assertEqual(kwargs["headers"]["Access-Token"], "fake-token")

    @patch("hc.api.transports.curl.request")
    def test_it_escapes_body(self, mock_post):
        mock_post.return_value.status_code = 200
        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.check)

        _, kwargs = mock_post.call_args
        self.assertEqual(
            kwargs["json"]["body"],
            'The check "Foo & Bar" received a ping and is now UP.',
        )
