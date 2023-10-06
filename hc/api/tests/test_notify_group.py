# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.utils.timezone import now
from django.test.utils import override_settings

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyGroupTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foobar"
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel_shell = Channel(project=self.project)
        self.channel_shell.kind = "shell"
        self.channel_shell.value = json.dumps({"cmd_down": "", "cmd_up": ""})
        self.channel_shell.save()

        self.channel_zulip = Channel(project=self.project)
        self.channel_zulip.kind = "zulip"
        self.channel_zulip.value = json.dumps(
            {
                "bot_email": "bot@example.org",
                "api_key": "fake-key",
                "mtype": "stream",
                "to": "general",
            }
        )
        self.channel_zulip.save()
        self.channel_zulip.checks.add(self.check)

        self.channel = Channel(project=self.project)
        self.channel.kind = "group"
        self.channel.value = ",".join(
            [str(self.channel_shell.code), str(self.channel_zulip.code)]
        )
        self.channel.save()
        self.channel.checks.add(self.check)

    def test_it_invalid_group_ids(self) -> None:
        self.channel.value = (
            "bda20a83-409c-4b2c-8e9b-589d408cd57b,40500bf8-0f37-4bb3-970c-9fe64b7ef39d"
        )
        self.channel.save()

        self.channel.notify(self.check)

        assert Notification.objects.count() == 1
        assert self.channel.last_error == ""

    @patch("hc.api.transports.curl.request")
    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_it_group(self, mock_system: Mock, mock_post: Mock) -> None:
        mock_system.return_value = 123
        mock_post.return_value.status_code = 200
        self.channel.notify(self.check)

        self.channel.refresh_from_db()
        assert self.channel.last_error == "1 out of 2 notifications failed"
