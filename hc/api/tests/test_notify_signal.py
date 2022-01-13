# coding: utf-8

from datetime import timedelta as td
import json
from unittest.mock import Mock, patch

from django.utils.timezone import now
from django.test.utils import override_settings
from hc.api.models import Channel, Check, Notification, TokenBucket
from hc.test import BaseTestCase


def setup_mock(socket, reply):
    # A mock of socket.socket object (the one with connect, send, recv etc. methods)
    socketobj = Mock()
    socketobj.recv.return_value = reply.encode()

    # The transport uses socket.socket() as a context manager,
    # so we replace the __enter__ method:
    socket.return_value.__enter__.return_value = socketobj

    # A convenience method for grabbing data passed to sendall
    socket.payload = lambda: socketobj.sendall.call_args[0][0].decode()


@override_settings(SIGNAL_CLI_SOCKET="/tmp/socket")
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

    @patch("hc.api.transports.socket.socket")
    def test_it_works(self, socket):
        setup_mock(socket, "{}\n")

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        self.assertIn("is DOWN", socket.payload())
        self.assertIn("+123456789", socket.payload())

        # Only one check in the project, so there should be no note about
        # other checks:
        self.assertNotIn("All the other checks are up.", socket.payload())

    @patch("hc.api.transports.socket.socket")
    def test_it_obeys_down_flag(self, socket):
        payload = {"value": "+123456789", "up": True, "down": False}
        self.channel.value = json.dumps(payload)
        self.channel.save()

        self.channel.notify(self.check)

        # This channel should not notify on "down" events:
        self.assertEqual(Notification.objects.count(), 0)

        self.assertFalse(socket.called)

    @patch("hc.api.transports.socket.socket")
    def test_it_requires_signal_cli_socket(self, socket):
        with override_settings(SIGNAL_CLI_SOCKET=None):
            self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Signal notifications are not enabled")

        self.assertFalse(socket.called)

    @patch("hc.api.transports.socket.socket")
    def test_it_does_not_escape_special_characters(self, socket):
        setup_mock(socket, "{}\n")

        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.check)

        self.assertIn("Foo & Bar", socket.payload())

    @override_settings(SECRET_KEY="test-secret")
    @patch("hc.api.transports.socket.socket")
    def test_it_obeys_rate_limit(self, socket):
        # "2862..." is sha1("+123456789test-secret")
        obj = TokenBucket(value="signal-2862991ccaa15c8856e7ee0abaf3448fb3c292e0")
        obj.tokens = 0
        obj.save()

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Rate limit exceeded")

        self.assertFalse(socket.called)

    @patch("hc.api.transports.socket.socket")
    def test_it_shows_all_other_checks_up_note(self, socket):
        setup_mock(socket, "{}\n")

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "up"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        self.assertIn("All the other checks are up.", socket.payload())

    @patch("hc.api.transports.socket.socket")
    def test_it_lists_other_down_checks(self, socket):
        setup_mock(socket, "{}\n")

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "down"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        self.assertIn("The following checks are also down", socket.payload())
        self.assertIn("Foobar", socket.payload())

    @patch("hc.api.transports.socket.socket")
    def test_it_does_not_show_more_than_10_other_checks(self, socket):
        setup_mock(socket, "{}\n")

        for i in range(0, 11):
            other = Check(project=self.project)
            other.name = f"Foobar #{i}"
            other.status = "down"
            other.last_ping = now() - td(minutes=61)
            other.save()

        self.channel.notify(self.check)

        self.assertNotIn("Foobar", socket.payload())
        self.assertIn("11 other checks are also down.", socket.payload())

    @patch("hc.api.transports.socket.socket")
    def test_it_handles_unregistered_user(self, socket):
        setup_mock(socket, '{"error":{"message": "UnregisteredUserException"}}\n')

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Recipient not found")

    @patch("hc.api.transports.socket.socket")
    def test_it_handles_error_code(self, socket):
        setup_mock(socket, '{"error":{"code": 123}}\n')

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "signal-cli call failed (123)")

    @patch("hc.api.transports.socket.socket")
    def test_it_handles_oserror(self, socket):
        socket.return_value.__enter__.return_value.sendall.side_effect = OSError("oops")

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "signal-cli call failed (oops)")
