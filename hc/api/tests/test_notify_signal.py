# coding: utf-8

from datetime import timedelta as td
import json
from unittest.mock import patch

from django.utils.timezone import now
from django.test.utils import override_settings
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


@override_settings(SIGNAL_CLI_USERNAME="+987654321")
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

    @patch("hc.api.transports.subprocess.run")
    def test_it_works(self, mock_run):
        mock_run.return_value.returncode = 0

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        self.assertTrue(mock_run.called)
        args, kwargs = mock_run.call_args
        cmd = " ".join(args[0])

        self.assertIn("-u +987654321", cmd)
        self.assertIn("send +123456789", cmd)

    @patch("hc.api.transports.subprocess.run")
    def test_it_obeys_down_flag(self, mock_run):
        payload = {"value": "+123456789", "up": True, "down": False}
        self.channel.value = json.dumps(payload)
        self.channel.save()

        self.channel.notify(self.check)

        # This channel should not notify on "down" events:
        self.assertEqual(Notification.objects.count(), 0)
        self.assertFalse(mock_run.called)

    @patch("hc.api.transports.subprocess.run")
    def test_it_requires_signal_cli_username(self, mock_run):

        with override_settings(SIGNAL_CLI_USERNAME=None):
            self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Signal notifications are not enabled")

        self.assertFalse(mock_run.called)

    @patch("hc.api.transports.subprocess.run")
    def test_it_does_not_escape_special_characters(self, mock_run):
        self.check.name = "Foo & Bar"
        self.check.save()

        mock_run.return_value.returncode = 0
        self.channel.notify(self.check)

        self.assertTrue(mock_run.called)
        args, kwargs = mock_run.call_args
        cmd = " ".join(args[0])

        self.assertIn("Foo & Bar", cmd)
