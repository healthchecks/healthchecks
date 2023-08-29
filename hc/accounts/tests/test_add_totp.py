from __future__ import annotations

from unittest.mock import Mock, patch

from hc.test import BaseTestCase


class AddTotpTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.url = "/accounts/two_factor/totp/"

    def test_it_requires_sudo_mode(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertContains(r, "We have sent a confirmation code")

    def test_it_shows_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertContains(r, "Enter the six-digit code")

        # It should put a "totp_secret" key in the session:
        self.assertIn("totp_secret", self.client.session)

    @patch("hc.accounts.views.pyotp.totp.TOTP")
    def test_it_adds_totp(self, mock_TOTP: Mock) -> None:
        mock_TOTP.return_value.verify.return_value = True

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"code": "000000"}
        r = self.client.post(self.url, payload, follow=True)
        self.assertRedirects(r, "/accounts/profile/")
        self.assertContains(r, "Successfully set up the Authenticator app")

        # totp_secret should be gone from the session:
        self.assertNotIn("totp_secret", self.client.session)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.totp)
        self.assertTrue(self.profile.totp_created)

    @patch("hc.accounts.views.pyotp.totp.TOTP")
    def test_it_handles_wrong_code(self, mock_TOTP: Mock) -> None:
        mock_TOTP.return_value.verify.return_value = False
        mock_TOTP.return_value.provisioning_uri.return_value = "test-uri"

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"code": "000000"}
        r = self.client.post(self.url, payload, follow=True)
        self.assertContains(r, "The code you entered was incorrect.")

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.totp)
        self.assertIsNone(self.profile.totp_created)

    def test_it_checks_if_totp_already_configured(self) -> None:
        self.profile.totp = "0" * 32
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 400)

    @patch("hc.accounts.views.pyotp.totp.TOTP")
    def test_it_handles_non_numeric_code(self, mock_TOTP: Mock) -> None:
        mock_TOTP.return_value.verify.return_value = False
        mock_TOTP.return_value.provisioning_uri.return_value = "test-uri"

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"code": "AAAAAA"}
        r = self.client.post(self.url, payload, follow=True)
        self.assertContains(r, "Enter a valid value")
