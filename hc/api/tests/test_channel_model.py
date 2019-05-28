import json

from hc.api.models import Channel
from hc.test import BaseTestCase


class ChannelModelTestCase(BaseTestCase):
    def test_webhook_spec_handles_plain_single_address(self):
        c = Channel(kind="webhook")
        c.value = "http://example.org"
        self.assertEqual(
            c.down_webhook_spec,
            {"method": "GET", "url": "http://example.org", "body": "", "headers": {}},
        )

        self.assertEqual(
            c.up_webhook_spec, {"method": "GET", "url": "", "body": "", "headers": {}}
        )

    def test_webhook_spec_handles_plain_pair(self):
        c = Channel(kind="webhook")
        c.value = "http://example.org\nhttp://example.com/up/"
        self.assertEqual(
            c.down_webhook_spec,
            {"method": "GET", "url": "http://example.org", "body": "", "headers": {}},
        )

        self.assertEqual(
            c.up_webhook_spec,
            {
                "method": "GET",
                "url": "http://example.com/up/",
                "body": "",
                "headers": {},
            },
        )

    def test_webhook_spec_handles_plain_post(self):
        c = Channel(kind="webhook")
        c.value = "http://example.org\n\nhello world"
        self.assertEqual(
            c.down_webhook_spec,
            {
                "method": "POST",
                "url": "http://example.org",
                "body": "hello world",
                "headers": {},
            },
        )

        self.assertEqual(
            c.up_webhook_spec,
            {"method": "POST", "url": "", "body": "hello world", "headers": {}},
        )

    def test_webhook_spec_handles_legacy_get(self):
        c = Channel(kind="webhook")
        c.value = json.dumps(
            {
                "url_down": "http://example.org",
                "url_up": "http://example.org/up/",
                "headers": {"X-Name": "value"},
                "post_data": "",
            }
        )

        self.assertEqual(
            c.down_webhook_spec,
            {
                "method": "GET",
                "url": "http://example.org",
                "body": "",
                "headers": {"X-Name": "value"},
            },
        )

        self.assertEqual(
            c.up_webhook_spec,
            {
                "method": "GET",
                "url": "http://example.org/up/",
                "body": "",
                "headers": {"X-Name": "value"},
            },
        )

    def test_webhook_spec_handles_legacy_post(self):
        c = Channel(kind="webhook")
        c.value = json.dumps(
            {
                "url_down": "http://example.org",
                "url_up": "http://example.org/up/",
                "headers": {"X-Name": "value"},
                "post_data": "hello world",
            }
        )

        self.assertEqual(
            c.down_webhook_spec,
            {
                "method": "POST",
                "url": "http://example.org",
                "body": "hello world",
                "headers": {"X-Name": "value"},
            },
        )

        self.assertEqual(
            c.up_webhook_spec,
            {
                "method": "POST",
                "url": "http://example.org/up/",
                "body": "hello world",
                "headers": {"X-Name": "value"},
            },
        )

    def test_webhook_spec_handles_mixed(self):
        c = Channel(kind="webhook")
        c.value = json.dumps(
            {
                "method_down": "GET",
                "url_down": "http://example.org",
                "body_down": "",
                "headers_down": {"X-Status": "X"},
                "method_up": "POST",
                "url_up": "http://example.org/up/",
                "body_up": "hello world",
                "headers_up": {"X-Status": "OK"},
            }
        )

        self.assertEqual(
            c.down_webhook_spec,
            {
                "method": "GET",
                "url": "http://example.org",
                "body": "",
                "headers": {"X-Status": "X"},
            },
        )

        self.assertEqual(
            c.up_webhook_spec,
            {
                "method": "POST",
                "url": "http://example.org/up/",
                "body": "hello world",
                "headers": {"X-Status": "OK"},
            },
        )
