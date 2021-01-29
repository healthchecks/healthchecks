# coding: utf-8

from datetime import timedelta as td
import json
from unittest.mock import patch

from django.core import mail
from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification, TokenBucket
from hc.test import BaseTestCase
from django.test.utils import override_settings


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

    @patch("hc.api.transports.requests.request")
    def test_pd(self, mock_post):
        self._setup_data("pd", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "123")

    @patch("hc.api.transports.requests.request")
    def test_pd_complex(self, mock_post):
        self._setup_data("pd", json.dumps({"service_key": "456"}))
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "456")

    @patch("hc.api.transports.requests.request")
    def test_pagertree(self, mock_post):
        self._setup_data("pagertree", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")

    @patch("hc.api.transports.requests.request")
    def test_pagerteam(self, mock_post):
        self._setup_data("pagerteam", "123")

        self.channel.notify(self.check)
        self.assertFalse(mock_post.called)
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.requests.request")
    def test_hipchat(self, mock_post):
        self._setup_data("hipchat", "123")

        self.channel.notify(self.check)
        self.assertFalse(mock_post.called)
        self.assertEqual(Notification.objects.count(), 0)

    @patch("hc.api.transports.requests.request")
    def test_victorops(self, mock_post):
        self._setup_data("victorops", "123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["message_type"], "CRITICAL")

    @patch("hc.api.transports.requests.request")
    def test_discord(self, mock_post):
        v = json.dumps({"webhook": {"url": "123"}})
        self._setup_data("discord", v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        attachment = payload["attachments"][0]
        fields = {f["title"]: f["value"] for f in attachment["fields"]}
        self.assertEqual(fields["Last Ping"], "an hour ago")

    @patch("hc.api.transports.requests.request")
    def test_discord_rewrites_discordapp_com(self, mock_post):
        v = json.dumps({"webhook": {"url": "https://discordapp.com/foo"}})
        self._setup_data("discord", v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        url = args[1]

        # discordapp.com is deprecated. For existing webhook URLs, wwe should
        # rewrite discordapp.com to discord.com:
        self.assertEqual(url, "https://discord.com/foo/slack")

    @patch("hc.api.transports.requests.request")
    def test_pushbullet(self, mock_post):
        self._setup_data("pushbullet", "fake-token")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["type"], "note")
        self.assertEqual(kwargs["headers"]["Access-Token"], "fake-token")

    @patch("hc.api.transports.requests.request")
    def test_telegram(self, mock_post):
        v = json.dumps({"id": 123})
        self._setup_data("telegram", v)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["chat_id"], 123)
        self.assertTrue("The check" in payload["text"])

    @patch("hc.api.transports.requests.request")
    def test_telegram_returns_error(self, mock_post):
        self._setup_data("telegram", json.dumps({"id": 123}))
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"description": "Hi"}

        self.channel.notify(self.check)
        n = Notification.objects.first()
        self.assertEqual(n.error, 'Received status code 400 with a message: "Hi"')

    def test_telegram_obeys_rate_limit(self):
        self._setup_data("telegram", json.dumps({"id": 123}))

        TokenBucket.objects.create(value="tg-123", tokens=0)

        self.channel.notify(self.check)
        n = Notification.objects.first()
        self.assertEqual(n.error, "Rate limit exceeded")

    @patch("hc.api.transports.requests.request")
    def test_call(self, mock_post):
        self.profile.call_limit = 1
        self.profile.save()

        value = {"label": "foo", "value": "+1234567890"}
        self._setup_data("call", json.dumps(value))
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertEqual(payload["To"], "+1234567890")

        n = Notification.objects.get()
        callback_path = f"/api/v1/notifications/{n.code}/status"
        self.assertTrue(payload["StatusCallback"].endswith(callback_path))

    @patch("hc.api.transports.requests.request")
    def test_call_limit(self, mock_post):
        # At limit already:
        self.profile.last_call_date = now()
        self.profile.calls_sent = 50
        self.profile.save()

        definition = {"value": "+1234567890"}
        self._setup_data("call", json.dumps(definition))

        self.channel.notify(self.check)
        self.assertFalse(mock_post.called)

        n = Notification.objects.get()
        self.assertTrue("Monthly phone call limit exceeded" in n.error)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertEqual(email.subject, "Monthly Phone Call Limit Reached")

    @patch("hc.api.transports.requests.request")
    def test_call_limit_reset(self, mock_post):
        # At limit, but also into a new month
        self.profile.calls_sent = 50
        self.profile.last_call_date = now() - td(days=100)
        self.profile.save()

        self._setup_data("sms", "+1234567890")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertTrue(mock_post.called)

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
        self.assertFalse(mock_system.called)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Shell commands are not enabled")
