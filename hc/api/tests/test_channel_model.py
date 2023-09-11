from __future__ import annotations

import json

from hc.api.models import Channel, WebhookSpec
from hc.test import BaseTestCase


class ChannelModelTestCase(BaseTestCase):
    def test_webhook_spec_handles_mixed(self) -> None:
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
            WebhookSpec(
                method="GET",
                url="http://example.org",
                body="",
                headers={"X-Status": "X"},
            ),
        )

        self.assertEqual(
            c.up_webhook_spec,
            WebhookSpec(
                method="POST",
                url="http://example.org/up/",
                body="hello world",
                headers={"X-Status": "OK"},
            ),
        )

    def test_it_handles_json_opsgenie_value(self) -> None:
        c = Channel(kind="opsgenie")
        c.value = json.dumps({"key": "abc", "region": "eu"})
        self.assertEqual(c.opsgenie.key, "abc")
        self.assertEqual(c.opsgenie.region, "eu")
