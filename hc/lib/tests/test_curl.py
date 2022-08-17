from unittest.mock import patch

from django.test import TestCase
from hc.lib.curl import request
import pycurl


class FakeCurl(object):
    def __init__(self, testclass):
        self.opts = {}
        self.testclass = testclass

    def setopt(self, k, v):
        self.opts[k] = v

    def perform(self):
        if pycurl.WRITEDATA in self.opts:
            self.opts[pycurl.WRITEDATA].write(b"hello world")

    def getinfo(self, _):
        return 200

    def close(self):
        pass


class CurlTestCase(TestCase):
    @patch("hc.lib.curl.pycurl.Curl")
    def test_get_works(self, mock):
        mock.return_value = obj = FakeCurl(self)
        response = request("get", "http://example.org")

        # URL should have been encoded to bytes
        self.assertEqual(obj.opts[pycurl.URL], b"http://example.org")

        # Default user agent
        self.assertEqual(obj.opts[pycurl.HTTPHEADER], ["User-Agent:healthchecks.io"])

        # It should allow redirects
        self.assertEqual(obj.opts[pycurl.FOLLOWLOCATION], True)
        self.assertEqual(obj.opts[pycurl.MAXREDIRS], 3)

        self.assertEqual(response.text, "hello world")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_handles_params(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("get", "http://example.org", params={"a": "b", "c": "d"})
        self.assertEqual(obj.opts[pycurl.URL], b"http://example.org?a=b&c=d")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_handles_auth(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("get", "http://example.org", auth=("alice", "pass"))
        self.assertEqual(obj.opts[pycurl.USERPWD], "alice:pass")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_allows_custom_ua(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("get", "http://example.org", headers={"User-Agent": "my-ua"})
        # The custom UA should override the default one
        self.assertEqual(obj.opts[pycurl.HTTPHEADER], ["User-Agent:my-ua"])

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_sets_timeout(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("get", "http://example.org", timeout=15)
        self.assertEqual(obj.opts[pycurl.TIMEOUT], 15)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_posts_form(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("post", "http://example.org", data={"a": "b", "c": "d"})
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "POST")
        self.assertEqual(obj.opts[pycurl.POSTFIELDS], "a=b&c=d")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_posts_str(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("post", "http://example.org", data="hello")
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "POST")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"hello")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 5)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_posts_bytes(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("post", "http://example.org", data=b"hello")
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "POST")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"hello")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 5)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_puts_form(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("put", "http://example.org", data={"a": "b", "c": "d"})
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "PUT")
        self.assertEqual(obj.opts[pycurl.POSTFIELDS], "a=b&c=d")

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_puts_str(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("put", "http://example.org", data="hello")
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "PUT")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"hello")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 5)

    @patch("hc.lib.curl.pycurl.Curl")
    def test_it_puts_bytes(self, mock):
        mock.return_value = obj = FakeCurl(self)
        request("put", "http://example.org", data=b"hello")
        self.assertEqual(obj.opts[pycurl.CUSTOMREQUEST], "PUT")
        self.assertEqual(obj.opts[pycurl.READDATA].getvalue(), b"hello")
        self.assertEqual(obj.opts[pycurl.INFILESIZE], 5)
