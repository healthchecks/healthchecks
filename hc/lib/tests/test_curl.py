from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pycurl
from django.test import SimpleTestCase
from django.test.utils import override_settings

from hc.lib.curl import CurlError, request


class FakeCurl(object):
    def __init__(self, ip: str = "1.2.3.4") -> None:
        self.opts: dict[int, Any] = {}
        self.ip = ip

    def setopt(self, k: int, v: Any) -> None:
        self.opts[k] = v

    def perform(self) -> None:
        if pycurl.OPENSOCKETFUNCTION in self.opts:
            # Simulate what libcurl would be doing here:
            # - if OPENSOCKETFUNCTION is defined, call it and pass it the ip address
            # - if the function returns pycurl.SOCKET_BAD, raise an error
            #
            # This is needed for test cases that exercise the
            # INTEGRATIONS_ALLOW_PRIVATE_IPS setting.
            callback = self.opts[pycurl.OPENSOCKETFUNCTION]
            address = (self.ip, 80)
            with patch("hc.lib.curl.socket"):
                sock = callback(pycurl.SOCKTYPE_IPCXN, (None, None, None, address))
                if sock == pycurl.SOCKET_BAD:
                    raise pycurl.error(pycurl.E_COULDNT_CONNECT)

        if pycurl.WRITEDATA in self.opts:
            self.opts[pycurl.WRITEDATA].write(b"hello world")

    def getinfo(self, _: int) -> int:
        return 200

    def close(self) -> None:
        pass


class CurlTestCase(SimpleTestCase):
    @patch("hc.lib.curl.pycurl.Curl")
    def test_get_works(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        response = request("get", "http://example.org")

        # URL should have been encoded to bytes
        self.assertEqual(obj.opts[pycurl.URL], b"http://example.org")

        # Default user agent
        self.assertEqual(obj.opts[pycurl.HTTPHEADER], [b"User-Agent:healthchecks.io"])

        # It should allow redirects
        self.assertEqual(obj.opts[pycurl.FOLLOWLOCATION], True)
        self.assertEqual(obj.opts[pycurl.MAXREDIRS], 3)

        self.assertEqual(response.text, "hello world")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_handles_params(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("get", "http://example.org", params={"a": "b", "c": "d"})
        self.assertEqual(obj.opts[pycurl.URL], b"http://example.org?a=b&c=d")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_handles_auth(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("get", "http://example.org", auth=("alice", "pass"))
        self.assertEqual(obj.opts[pycurl.USERPWD], "alice:pass")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_allows_custom_ua(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("get", "http://example.org", headers={"User-Agent": "my-ua"})
        # The custom UA should override the default one
        self.assertEqual(obj.opts[pycurl.HTTPHEADER], [b"User-Agent:my-ua"])

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_encodes_header_values_to_latin1(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("get", "http://example.org", headers={"User-Agent": "À"})
        self.assertEqual(obj.opts[pycurl.HTTPHEADER], [b"User-Agent:\xc0"])

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_sets_timeout(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("get", "http://example.org", timeout=15)
        self.assertEqual(obj.opts[pycurl.TIMEOUT], 15)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_posts_form(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("post", "http://example.org", data={"a": "b", "c": "d"})
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "POST")
        self.assertEqual(obj.opts[pycurl.POSTFIELDS], "a=b&c=d")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_posts_str(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("post", "http://example.org", data="hello")
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "POST")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"hello")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 5)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_posts_bytes(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("post", "http://example.org", data=b"hello")
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "POST")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"hello")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 5)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_posts_json(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("post", "http://example.org", json=[1, 2, 3])
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "POST")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"[1, 2, 3]")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 9)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_puts_form(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("put", "http://example.org", data={"a": "b", "c": "d"})
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "PUT")
        self.assertEqual(obj.opts[pycurl.POSTFIELDS], "a=b&c=d")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_puts_str(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("put", "http://example.org", data="hello")
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "PUT")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"hello")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 5)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_puts_bytes(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("put", "http://example.org", data=b"hello")
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "PUT")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"hello")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 5)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_puts_json(self, mock: Mock) -> None:
        mock.return_value = obj = FakeCurl()
        request("put", "http://example.org", json=[1, 2, 3])
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "PUT")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"[1, 2, 3]")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 9)

    @override_settings(INTEGRATIONS_ALLOW_PRIVATE_IPS=False)
    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_rejects_private_ip(self, mock: Mock) -> None:
        mock.return_value = FakeCurl(ip="127.0.0.1")
        with self.assertRaises(CurlError) as cm:
            request("get", "http://example.org")
        self.assertEqual(
            cm.exception.message,
            "Connections to private IP addresses are not allowed",
        )

    @override_settings(INTEGRATIONS_ALLOW_PRIVATE_IPS=True)
    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_accepts_private_ip(self, mock: Mock) -> None:
        mock.return_value = FakeCurl(ip="127.0.0.1")
        request("get", "http://example.org")
