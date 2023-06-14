# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.core import mail
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyTestCase(BaseTestCase):
    def _setup_data(self, kind, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = kind
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_pagerteam(self, mock_post):
        self._setup_data("pagerteam", "123")

        self.channel.notify(self.check)
        mock_post.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.curl.request")
    def test_hipchat(self, mock_post):
        self._setup_data("hipchat", "123")

        self.channel.notify(self.check)
        mock_post.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.curl.request")
    def test_call(self, mock_post):
        self.profile.call_limit = 1
        self.profile.save()

        value = {"label": "foo", "value": "+1234567890"}
        self._setup_data("call", json.dumps(value))
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["To"], "+1234567890")

        n = Notification.objects.get()
        callback_path = f"/api/v3/notifications/{n.code}/status"
        self.assertTrue(payload["StatusCallback"].endswith(callback_path))

    @patch("hc.api.transports.curl.request")
    def test_call_limit(self, mock_post):
        # At limit already:
        self.profile.call_limit = 50
        self.profile.last_call_date = now()
        self.profile.calls_sent = 50
        self.profile.save()

        definition = {"value": "+1234567890"}
        self._setup_data("call", json.dumps(definition))

        self.channel.notify(self.check)
        mock_post.assert_not_called()

        n = Notification.objects.get()
        self.assertTrue("Monthly phone call limit exceeded" in n.error)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertEqual(email.subject, "Monthly Phone Call Limit Reached")

    @patch("hc.api.transports.curl.request")
    def test_call_limit_reset(self, mock_post):
        # At limit, but also into a new month
        self.profile.call_limit = 50
        self.profile.calls_sent = 50
        self.profile.last_call_date = now() - td(days=100)
        self.profile.save()

        self._setup_data("call", "+1234567890")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        mock_post.assert_called_once()

    def test_not_implimented(self):
        self._setup_data("webhook", "http://example")
        self.channel.kind = "invalid"

        with self.assertRaises(NotImplementedError):
            self.channel.notify(self.check)

    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell(self, mock_system):
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 0

        self.channel.notify(self.check)
        mock_system.assert_called_with("logger hello")

    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell_handles_nonzero_exit_code(self, mock_system):
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 123

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Command returned exit code 123")

    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=True)
    def test_shell_supports_variables(self, mock_system):
        definition = {"cmd_down": "logger $NAME is $STATUS ($TAG1)", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))
        mock_system.return_value = 0

        self.check.name = "Database"
        self.check.tags = "foo bar"
        self.check.save()
        self.channel.notify(self.check)

        mock_system.assert_called_with("logger Database is down (foo)")

    @patch("hc.api.transports.os.system")
    @override_settings(SHELL_ENABLED=False)
    def test_shell_disabled(self, mock_system):
        definition = {"cmd_down": "logger hello", "cmd_up": ""}
        self._setup_data("shell", json.dumps(definition))

        self.channel.notify(self.check)
        mock_system.assert_not_called()

        n = Notification.objects.get()
        self.assertEqual(n.error, "Shell commands are not enabled")
