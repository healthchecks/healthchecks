# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification
from hc.test import BaseTestCase


class NotifyTestCase(BaseTestCase):
    def _setup_data(
        self, kind: str, value: str, status: str = "down", email_verified: bool = True
    ) -> None:
        self.check = Check(project=self.project)
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = kind
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = status

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_pagerteam(self, mock_post: Mock) -> None:
        self._setup_data("pagerteam", "123")

        self.channel.notify(self.flip)
        mock_post.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_hipchat(self, mock_post: Mock) -> None:
        self._setup_data("hipchat", "123")

        self.channel.notify(self.flip)
        mock_post.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)

    def test_not_implemented(self) -> None:
        self._setup_data("webhook", "http://example")
        self.channel.kind = "invalid"

        with self.assertRaises(NotImplementedError):
            self.channel.notify(self.flip)

    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 0

        self.channel.notify(self.flip)
        mock_system.assert_called_with("logger hello")

    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell_handles_nonzero_exit_code(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 123

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Command returned exit code 123")

    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell_supports_variables(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger $NAME is $STATUS ($TAG1)", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 0

        self.check.name = "Database"
        self.check.tags = "foo bar"
        self.check.save()
        self.channel.notify(self.flip)

        mock_system.assert_called_with("logger Database is down (foo)")

    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=False)
    def test_shell_disabled(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))

        self.channel.notify(self.flip)
        mock_system.assert_not_called()

        n = Notification.objects.get()
        self.assertEqual(n.error, "Shell commands are not enabled")
