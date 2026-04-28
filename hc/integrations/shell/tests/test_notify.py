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

    @patch("hc.integrations.shell.transport.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 0

        self.channel.notify(self.flip)
        mock_system.assert_called_with("logger hello")

    @patch("hc.integrations.shell.transport.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell_handles_nonzero_exit_code(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 123

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Command returned exit code 123")

    @patch("hc.integrations.shell.transport.os.system")
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

    @patch("hc.integrations.shell.transport.os.system")
    @override_settings(SHELL_ENABLED=False)
    def test_shell_disabled(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))

        self.channel.notify(self.flip)
        mock_system.assert_not_called()

        n = Notification.objects.get()
        self.assertEqual(n.error, "Shell commands are not enabled")

    @patch("hc.integrations.shell.transport.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell_escapes_name(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger $NAME", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 0

        samples = {
            "a&b": "logger 'a&b'",
            "a'b": """logger 'a'"'"'b'""",
        }

        for name, escaped_cmd in samples.items():
            self.check.name = name
            self.check.save()
            self.channel.notify(self.flip)

            mock_system.assert_called_with(escaped_cmd)

    @patch("hc.integrations.shell.transport.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell_escapes_tags(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger $TAGS", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 0

        samples = {
            "a&b": "logger 'a&b'",
            "a'b": """logger 'a'"'"'b'""",
        }

        for tags, escaped_cmd in samples.items():
            self.check.tags = tags
            self.check.save()
            self.channel.notify(self.flip)

            mock_system.assert_called_with(escaped_cmd)

    @patch("hc.integrations.shell.transport.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell_escapes_tag1(self, mock_system: Mock) -> None:
        definition = {"cmd_down": "logger $TAG1", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 0

        samples = {
            "a&b anothertag": "logger 'a&b'",
            "a'b anothertag": """logger 'a'"'"'b'""",
        }

        for tags, escaped_cmd in samples.items():
            self.check.tags = tags
            self.check.save()
            self.channel.notify(self.flip)

            mock_system.assert_called_with(escaped_cmd)
