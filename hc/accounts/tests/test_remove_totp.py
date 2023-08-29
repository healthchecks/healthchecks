from __future__ import annotations

from hc.accounts.models import Credential
from hc.test import BaseTestCase


class RemoveCredentialTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.profile.totp = "0" * 32
        self.profile.save()

        self.url = "/accounts/two_factor/totp/remove/"

    def test_it_requires_sudo_mode(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertContains(r, "We have sent a confirmation code")

    def test_it_shows_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertContains(r, "Disable Authenticator App")
        self.assertContains(r, "two-factor authentication will no longer be active")

    def test_it_skips_warning_when_other_2fa_methods_exist(self) -> None:
        self.c = Credential.objects.create(user=self.alice, name="Alices Key")
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertNotContains(r, "two-factor authentication will no longer be active")

    def test_it_removes_totp(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.post(self.url, {"disable_totp": "1"}, follow=True)
        self.assertRedirects(r, "/accounts/profile/")
        self.assertContains(r, "Disabled the authenticator app.")

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.totp)
        self.assertIsNone(self.profile.totp_created)
