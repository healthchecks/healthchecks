# coding: utf-8

from __future__ import annotations

import json
from unittest.mock import Mock, patch

from django.test.utils import override_settings

from hc.test import BaseTestCase

# Address is either a string (the path to the unix socket)
# or a host:port tuple.
Address = str | tuple[str, int]


class MockSocket(object):
    def __init__(self, response_tmpl: dict[str, str]) -> None:
        self.response_tmpl = response_tmpl
        self.req = None
        self.outbox = b""

    def settimeout(self, seconds: int) -> None:
        pass

    def connect(self, socket_path: Address) -> None:
        pass

    def shutdown(self, flags: int) -> None:
        pass

    def sendall(self, data: bytes) -> None:
        self.req = json.loads(data.decode())
        assert self.req
        self.response_tmpl["id"] = self.req["id"]

        message = json.dumps(self.response_tmpl) + "\n"
        self.outbox += message.encode()

    def recv(self, nbytes: int) -> bytes:
        head, self.outbox = self.outbox[0:1], self.outbox[1:]
        return head


def setup_mock(socket: Mock, response_tmpl: dict[str, str]) -> MockSocket:
    # A mock of socket.socket object
    socketobj = MockSocket(response_tmpl)

    # The transport uses socket.socket() as a context manager,
    # so we replace the __enter__ method:
    socket.return_value.__enter__.return_value = socketobj

    return socketobj


@override_settings(SIGNAL_CLI_SOCKET="/tmp/socket")
class SignalCaptchaTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.alice.is_superuser = True
        self.alice.save()

        self.url = "/signal_captcha/"

    @patch("hc.api.transports.socket.socket")
    def test_it_works(self, socket: Mock) -> None:
        socketobj = setup_mock(socket, {"result": "all good"})

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"challenge": "foo", "captcha": "bar"})
        self.assertContains(r, "all good")

        assert socketobj.req
        params = socketobj.req["params"]
        self.assertEqual(params["challenge"], "foo")
        self.assertEqual(params["captcha"], "bar")

    @patch("hc.api.transports.socket.socket")
    def test_it_removes_protocol_prefix(self, socket: Mock) -> None:
        socketobj = setup_mock(socket, {})

        self.client.login(username="alice@example.org", password="password")
        self.client.post(
            self.url, {"challenge": "foo", "captcha": "signalcaptcha://bar"}
        )

        assert socketobj.req
        params = socketobj.req["params"]
        self.assertEqual(params["captcha"], "bar")

    def test_it_requires_superuser(self) -> None:
        self.alice.is_superuser = False
        self.alice.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"challenge": "foo", "captcha": "bar"})
        self.assertEqual(r.status_code, 403)

    @patch("hc.api.transports.socket.socket")
    def test_it_requires_signal_cli_socket(self, socket: Mock) -> None:
        with override_settings(SIGNAL_CLI_SOCKET=None):
            self.client.login(username="alice@example.org", password="password")
            r = self.client.post(self.url, {"challenge": "foo", "captcha": "bar"})
            self.assertEqual(r.status_code, 404)

        socket.assert_not_called()

    @patch("hc.api.transports.socket.socket")
    def test_it_checks_jsonrpc_id(self, socket: Mock) -> None:
        socketobj = setup_mock(socket, {"result": "all good"})
        # Add a message with an unexpected id in the outbox.
        # The socket reader should skip over it.
        socketobj.outbox += b'{"id": "surprise"}\n'

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"challenge": "foo", "captcha": "bar"})
        self.assertContains(r, "all good")
