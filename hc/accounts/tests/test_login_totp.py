from __future__ import annotations

import time
from unittest.mock import Mock, patch

from hc.api.models import TokenBucket
from hc.test import BaseTestCase


class LoginTotpTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        # This is the user we're trying to authenticate
        session = self.client.session
        session["2fa_user"] = [self.alice.id, self.alice.email, (time.time()) + 300]
        session.save()

        self.profile.totp = "0" * 32
        self.profile.save()

        self.url = "/accounts/login/two_factor/totp/"
        self.checks_url = f"/projects/{self.project.code}/checks/"

    def test_it_shows_form(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(r, "Please enter the six-digit code")

    def test_it_requires_unauthenticated_user(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 400)

    def test_it_requires_totp_secret(self) -> None:
        self.profile.totp = None
        self.profile.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_changed_email(self) -> None:
        session = self.client.session
        session["2fa_user"] = [self.alice.id, "eve@example.org", int(time.time())]
        session.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_old_timestamp(self) -> None:
        session = self.client.session
        session["2fa_user"] = [self.alice.id, self.alice.email, int(time.time()) - 310]
        session.save()

        r = self.client.get(self.url)
        self.assertRedirects(r, "/accounts/login/")

    @patch("hc.accounts.views.pyotp.totp.TOTP")
    def test_it_logs_in(self, mock_TOTP: Mock) -> None:
        mock_TOTP.return_value.verify.return_value = True

        r = self.client.post(self.url, {"code": "000000"})
        self.assertRedirects(r, self.checks_url)

        self.assertNotIn("2fa_user_id", self.client.session)

    @patch("hc.accounts.views.pyotp.totp.TOTP")
    def test_it_redirects_after_login(self, mock_TOTP: Mock) -> None:
        mock_TOTP.return_value.verify.return_value = True

        url = self.url + "?next=" + self.channels_url
        r = self.client.post(url, {"code": "000000"})
        self.assertRedirects(r, self.channels_url)

    @patch("hc.accounts.views.pyotp.totp.TOTP")
    def test_it_handles_authentication_failure(self, mock_TOTP: Mock) -> None:
        mock_TOTP.return_value.verify.return_value = False

        r = self.client.post(self.url, {"code": "000000"})
        self.assertContains(r, "The code you entered was incorrect.")

    def test_it_uses_rate_limiting(self) -> None:
        obj = TokenBucket(value=f"totp-{self.alice.id}")
        obj.tokens = 0
        obj.save()

        r = self.client.post(self.url, {"code": "000000"})
        self.assertContains(r, "Too Many Requests")

    @patch("hc.accounts.views.pyotp.totp.TOTP")
    def test_it_rejects_used_code(self, mock_TOTP: Mock) -> None:
        mock_TOTP.return_value.verify.return_value = True

        obj = TokenBucket(value=f"totpc-{self.alice.id}-000000")
        obj.tokens = 0
        obj.save()

        r = self.client.post(self.url, {"code": "000000"})
        self.assertContains(r, "Too Many Requests")
