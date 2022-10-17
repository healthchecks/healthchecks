from __future__ import annotations

import json

from hc.api.models import Channel
from hc.test import BaseTestCase


class ChannelModelTestCase(BaseTestCase):
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

    def test_it_handles_legacy_opsgenie_value(self):
        c = Channel(kind="opsgenie", value="foo123")
        self.assertEqual(c.opsgenie_key, "foo123")
        self.assertEqual(c.opsgenie_region, "us")

    def test_it_handles_json_opsgenie_value(self):
        c = Channel(kind="opsgenie")
        c.value = json.dumps({"key": "abc", "region": "eu"})
        self.assertEqual(c.opsgenie_key, "abc")
        self.assertEqual(c.opsgenie_region, "eu")

    def test_it_handles_legacy_sms_json_value(self):
        c = Channel(kind="sms", value=json.dumps({"value": "+123123123"}))
        self.assertTrue(c.sms_notify_down)
        self.assertFalse(c.sms_notify_up)
