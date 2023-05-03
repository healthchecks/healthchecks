# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification, Ping
from hc.test import BaseTestCase


class NotifyDiscordTestCase(BaseTestCase):
    def _setup_data(self, value, status="down"):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=61)
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "discord"
        self.channel.value = value
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        v = json.dumps({"webhook": {"url": "https://example.org"}})
        self._setup_data(v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        self.assertEqual(url, "https://example.org/slack")

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Success, an hour ago")

    @patch("hc.api.transports.curl.request")
    def test_it_rewrites_discordapp_com(self, mock_post):
        v = json.dumps({"webhook": {"url": "https://discordapp.com/foo"}})
        self._setup_data(v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        url = mock_post.call_args.args[1]
        # discordapp.com is deprecated. For existing webhook URLs, we should
        # rewrite discordapp.com to discord.com:
        self.assertEqual(url, "https://discord.com/foo/slack")

    @patch("hc.api.transports.curl.request")
    def test_it_handles_last_ping_failure(self, mock_post):
        v = json.dumps({"webhook": {"url": "123"}})
        self._setup_data(v)
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.save()

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        attachment = mock_post.call_args.kwargs["json"]["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "Failure, an hour ago")
