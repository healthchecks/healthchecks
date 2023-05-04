# coding: utf-8

from __future__ import annotations

import json
import logging
from datetime import timedelta as td
from unittest.mock import patch

from django.core import mail
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification, Ping, TokenBucket
from hc.test import BaseTestCase


class MockSocket(object):
    def __init__(self, response_tmpl, side_effect=None):
        self.response_tmpl = response_tmpl
        self.side_effect = side_effect
        self.address = None
        self.req = None
        self.outbox = b""

    def settimeout(self, seconds):
        pass

    def connect(self, address):
        self.address = address

    def shutdown(self, flags):
        pass

    def sendall(self, data):
        if self.side_effect:
            raise self.side_effect

        self.req = json.loads(data.decode())
        self.response_tmpl["id"] = self.req["id"]

        message = json.dumps(self.response_tmpl) + "\n"
        self.outbox += message.encode()

    def recv(self, nbytes):
        head, self.outbox = self.outbox[0:1], self.outbox[1:]
        return head


def setup_mock(socket, response_tmpl, side_effect=None):
    # A mock of socket.socket object
    socketobj = MockSocket(response_tmpl, side_effect)

    # The transport uses socket.socket() as a context manager,
    # so we replace the __enter__ method:
    socket.return_value.__enter__.return_value = socketobj

    return socketobj


@override_settings(SIGNAL_CLI_SOCKET="/tmp/socket")
class NotifySignalTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Daily Backup"
        self.check.tags = "foo bar"
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.n_pings = 123
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.n = 1
        self.ping.remote_addr = "1.2.3.4"
        self.ping.body_raw = b"Body Line 1\nBody Line 2"
        self.ping.save()

        payload = {"value": "+123456789", "up": True, "down": True}
        self.channel = Channel(project=self.project)
        self.channel.kind = "signal"
        self.channel.value = json.dumps(payload)
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.socket.socket")
    def test_it_works(self, socket):
        socketobj = setup_mock(socket, {})

        self.channel.notify(self.check)
        self.assertEqual(socketobj.address, "/tmp/socket")

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        params = socketobj.req["params"]
        self.assertIn("“Daily Backup” is DOWN", params["message"])
        self.assertIn("Project: Alices Project", params["message"])
        self.assertIn("Tags: foo, bar", params["message"])
        self.assertIn("Period: 1 day", params["message"])
        self.assertIn("Total Pings: 123", params["message"])
        self.assertIn("Last Ping: Success, now", params["message"])
        self.assertIn("+123456789", params["recipient"])

        # Only one check in the project, so there should be no note about
        # other checks:
        self.assertNotIn("All the other checks are up.", params["message"])

    @patch("hc.api.transports.socket.socket")
    def test_it_handles_special_characters(self, socket):
        socketobj = setup_mock(socket, {})

        self.project.name = "Alice & Friends"
        self.project.save()

        self.check.name = "Foo & Co"
        self.check.tags = "foo a&b"
        self.check.save()

        self.channel.notify(self.check)
        self.assertEqual(socketobj.address, "/tmp/socket")

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        params = socketobj.req["params"]
        self.assertIn("“Foo & Co” is DOWN", params["message"])
        self.assertIn("Project: Alice & Friends", params["message"])
        self.assertIn("Tags: foo, a&b", params["message"])

    @override_settings(SIGNAL_CLI_SOCKET="example.org:1234")
    @patch("hc.api.transports.socket.socket")
    def test_it_handles_host_port(self, socket):
        socketobj = setup_mock(socket, {})

        self.channel.notify(self.check)
        self.assertEqual(socketobj.address, ("example.org", 1234))

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

    @patch("hc.api.transports.socket.socket")
    def test_it_obeys_down_flag(self, socket):
        payload = {"value": "+123456789", "up": True, "down": False}
        self.channel.value = json.dumps(payload)
        self.channel.save()

        self.channel.notify(self.check)

        # This channel should not notify on "down" events:
        self.assertEqual(Notification.objects.count(), 0)
        socket.assert_not_called()

    @patch("hc.api.transports.socket.socket")
    def test_it_requires_signal_cli_socket(self, socket):
        with override_settings(SIGNAL_CLI_SOCKET=None):
            self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Signal notifications are not enabled")
        socket.assert_not_called()

    @patch("hc.api.transports.socket.socket")
    def test_it_does_not_escape_special_characters(self, socket):
        socketobj = setup_mock(socket, {})

        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.check)

        self.assertIn("Foo & Bar", socketobj.req["params"]["message"])

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
        socket.assert_not_called()

    @patch("hc.api.transports.socket.socket")
    def test_it_shows_all_other_checks_up_note(self, socket):
        socketobj = setup_mock(socket, {})

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "up"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        message = socketobj.req["params"]["message"]
        self.assertIn("All the other checks are up.", message)

    @patch("hc.api.transports.socket.socket")
    def test_it_lists_other_down_checks(self, socket):
        socketobj = setup_mock(socket, {})

        other = Check(project=self.project)
        other.name = "Foobar & Co"
        other.status = "down"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        message = socketobj.req["params"]["message"]
        self.assertIn("The following checks are also down", message)
        self.assertIn("Foobar & Co", message)

    @patch("hc.api.transports.socket.socket")
    def test_it_does_not_show_more_than_10_other_checks(self, socket):
        socketobj = setup_mock(socket, {})

        for i in range(0, 11):
            other = Check(project=self.project)
            other.name = f"Foobar #{i}"
            other.status = "down"
            other.last_ping = now() - td(minutes=61)
            other.save()

        self.channel.notify(self.check)

        message = socketobj.req["params"]["message"]
        self.assertNotIn("Foobar", message)
        self.assertIn("11 other checks are also down.", message)

    @patch("hc.api.transports.socket.socket")
    def test_it_handles_unregistered_failure(self, socket):
        msg = {
            "error": {
                "code": -1,
                "message": "Failed to send message",
                "data": {
                    "response": {
                        "results": [
                            {
                                "recipientAddress": {"number": "+123456789"},
                                "type": "UNREGISTERED_FAILURE",
                            }
                        ],
                    }
                },
            },
        }
        setup_mock(socket, msg)

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Recipient not found")

    @patch("hc.api.transports.socket.socket")
    def test_it_handles_error_code(self, socket):
        setup_mock(socket, {"error": {"code": 123}})

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "signal-cli call failed (123)")

    @patch("hc.api.transports.socket.socket")
    def test_it_handles_oserror(self, socket):
        setup_mock(socket, {}, side_effect=OSError("oops"))

        logging.disable(logging.CRITICAL)
        self.channel.notify(self.check)
        logging.disable(logging.NOTSET)

        n = Notification.objects.get()
        self.assertEqual(n.error, "signal-cli call failed (oops)")

    @patch("hc.api.transports.socket.socket")
    def test_it_checks_jsonrpc_id(self, socket):
        socketobj = setup_mock(socket, {})
        # Add a message with an unexpected id in the outbox.
        # The socket reader should skip over it.
        socketobj.outbox += b'{"id": "surprise"}\n'

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        # outbox should be empty now
        self.assertEqual(socketobj.outbox, b"")

    @override_settings(ADMINS=[("Admin", "admin@example.org")])
    @patch("hc.api.transports.socket.socket")
    def test_it_handles_rate_limit_failure(self, socket):
        msg = {
            "error": {
                "code": -1,
                "message": "Failed to send message",
                "data": {
                    "response": {
                        "results": [
                            {
                                "recipientAddress": {"number": "+123456789"},
                                "type": "RATE_LIMIT_FAILURE",
                                "token": "fddc87d7-572a-4559-9081-b41e3bc25254",
                            }
                        ],
                    }
                },
            },
        }
        setup_mock(socket, msg)

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "CAPTCHA proof required")

        emails = {email.to[0]: email for email in mail.outbox}

        # It should notify ADMINS
        email = emails["admin@example.org"]
        self.assertEqual(email.subject, "[Django] Signal CAPTCHA proof required")

        # It should notify the user
        email = emails["alice@example.org"]
        self.assertEqual(
            email.subject,
            "Signal notification failed: The check “Daily Backup” is DOWN.",
        )

    @patch("hc.api.transports.socket.socket")
    def test_it_handles_null_data(self, socket):
        msg = {
            "error": {
                "code": -32602,
                "message": "Method requires valid account parameter",
                "data": None,
            },
        }
        setup_mock(socket, msg)

        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "signal-cli call failed (-32602)")
