from __future__ import annotations

from hc.front.validators import WebhookValidator
from hc.test import BaseTestCase


class WebhookValidatorTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.v = WebhookValidator()

    def test_it_does_not_touch_existing_tld(self):
        self.assertEqual(self.v.add_tld("http://example.org"), "http://example.org")

    def test_it_does_not_touch_existing_tld_with_port(self):
        self.assertEqual(
            self.v.add_tld("http://example.org:80"), "http://example.org:80"
        )

    def test_it_does_not_touch_existing_tld_with_port_and_basic_auth(self):
        self.assertEqual(
            self.v.add_tld("http://user:pass@example.org:80"),
            "http://user:pass@example.org:80",
        )

    def test_it_adds_tld(self):
        self.assertEqual(self.v.add_tld("http://example"), "http://example.dummytld")

    def test_it_handles_trailing_dot(self):
        self.assertEqual(self.v.add_tld("http://example."), "http://example.dummytld")

    def test_it_handles_port(self):
        self.assertEqual(
            self.v.add_tld("http://example:80"), "http://example.dummytld:80"
        )

    def test_it_handles_port_and_basic_auth(self):
        self.assertEqual(
            self.v.add_tld("http://user:pass@example:80"),
            "http://user:pass@example.dummytld:80",
        )
