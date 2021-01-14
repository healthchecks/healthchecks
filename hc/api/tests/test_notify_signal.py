# coding: utf-8

from datetime import timedelta as td
import json
from unittest.mock import patch

from django.utils.timezone import now
from django.test.utils import override_settings
from hc.api.models import Channel, Check, Notification, TokenBucket
from hc.test import BaseTestCase


@override_settings(SIGNAL_CLI_ENABLED=True)
class NotifySignalTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Daily Backup"
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        payload = {"value": "+123456789", "up": True, "down": True}
        self.channel = Channel(project=self.project)
        self.channel.kind = "signal"
        self.channel.value = json.dumps(payload)
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.dbus")
    def test_it_works(self, mock_bus):
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        args, kwargs = mock_bus.SystemBus.return_value.call_blocking.call_args
        message, attachments, recipients = args[-1]

        self.assertIn("is DOWN", message)
        self.assertEqual(recipients, ["+123456789"])

    @patch("hc.api.transports.dbus")
    def test_it_obeys_down_flag(self, mock_bus):
        payload = {"value": "+123456789", "up": True, "down": False}
        self.channel.value = json.dumps(payload)
        self.channel.save()

        self.channel.notify(self.check)

        # This channel should not notify on "down" events:
        self.assertEqual(Notification.objects.count(), 0)

        self.assertFalse(mock_bus.SystemBus.called)

    @patch("hc.api.transports.dbus")
    def test_it_requires_signal_cli_enabled(self, mock_bus):
        with override_settings(SIGNAL_CLI_ENABLED=False):
            self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Signal notifications are not enabled")

        self.assertFalse(mock_bus.SystemBus.called)

    @patch("hc.api.transports.dbus")
    def test_it_does_not_escape_special_characters(self, mock_bus):
        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.check)

        args, kwargs = mock_bus.SystemBus.return_value.call_blocking.call_args
        message, attachments, recipients = args[-1]
        self.assertIn("Foo & Bar", message)

    @override_settings(SECRET_KEY="test-secret")
    @patch("hc.api.transports.dbus")
    def test_it_obeys_rate_limit(self, mock_bus):
        # "2862..." is sha1("+123456789test-secret")
        obj = TokenBucket(value="signal-2862991ccaa15c8856e7ee0abaf3448fb3c292e0")
        obj.tokens = 0
        obj.save()

        self.channel.notify(self.check)
        n = Notification.objects.first()
        self.assertEqual(n.error, "Rate limit exceeded")

        self.assertFalse(mock_bus.SysemBus.called)
