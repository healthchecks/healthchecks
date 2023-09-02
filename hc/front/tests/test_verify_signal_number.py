# coding: utf-8

from __future__ import annotations

from unittest.mock import Mock, patch

from django.test.utils import override_settings

from hc.api.models import TokenBucket
from hc.api.transports import TransportError
from hc.test import BaseTestCase


@override_settings(SIGNAL_CLI_SOCKET="/tmp/socket")
class VerifySignalNumberTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.url = "/signal_verify/"

    @patch("hc.front.views.Signal")
    def test_it_works(self, mock_signal: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"phone": "+1234567890"})
        self.assertContains(r, "All good, the message was sent")

    @patch("hc.front.views.Signal")
    def test_it_handles_rate_limit(self, mock_signal: Mock) -> None:
        mock_signal.send.side_effect = TransportError("CAPTCHA proof required")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"phone": "+1234567890"})
        self.assertContains(r, "We hit a Signal rate-limit")

    @patch("hc.front.views.Signal")
    def test_it_handles_recipient_not_found(self, mock_signal: Mock) -> None:
        mock_signal.send.side_effect = TransportError("Recipient not found")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"phone": "+1234567890"})
        self.assertContains(r, "Recipient not found")

    @patch("hc.front.views.Signal")
    def test_it_handles_unhandled_error(self, mock_signal: Mock) -> None:
        mock_signal.send.side_effect = TransportError("signal-cli call failed (123)")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"phone": "+1234567890"})
        self.assertContains(r, "signal-cli call failed")

    @patch("hc.front.views.Signal")
    def test_it_handles_invalid_phone_number(self, mock_signal: Mock) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"phone": "+123"})
        self.assertContains(r, "Invalid phone number")

    def test_it_requires_post(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_requires_authenticated_user(self) -> None:
        r = self.client.post(self.url, {"phone": "+1234567890"})
        self.assertRedirects(r, "/accounts/login/?next=" + self.url)

    def test_it_obeys_per_account_rate_limit(self) -> None:
        TokenBucket.objects.create(value=f"signal-verify-{self.alice.id}", tokens=0)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"phone": "+1234567890"})
        self.assertContains(r, "Verification rate limit exceeded")

    @override_settings(SECRET_KEY="test-secret")
    def test_it_obeys_per_recipient_rate_limit(self) -> None:
        # "2862..." is sha1("+123456789test-secret")
        obj = TokenBucket(value="signal-2862991ccaa15c8856e7ee0abaf3448fb3c292e0")
        obj.tokens = 0
        obj.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"phone": "+123456789"})
        self.assertContains(r, "Verification rate limit exceeded")
