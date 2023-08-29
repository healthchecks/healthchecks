from __future__ import annotations

from django.test.utils import override_settings

from hc.accounts.models import Credential
from hc.test import BaseTestCase


@override_settings(RP_ID="testserver")
class RemoveCredentialTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.c = Credential.objects.create(user=self.alice, name="Alices Key")
        self.url = f"/accounts/two_factor/{self.c.code}/remove/"

    def test_it_requires_sudo_mode(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertContains(r, "We have sent a confirmation code")

    @override_settings(RP_ID=None)
    def test_it_requires_rp_id(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertContains(r, "Remove Security Key")
        self.assertContains(r, "Alices Key")
        self.assertContains(r, "two-factor authentication will no longer be active")

    def test_it_skips_warning_when_other_2fa_methods_exist(self) -> None:
        self.profile.totp = "0" * 32
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertNotContains(r, "two-factor authentication will no longer be active")

    def test_it_removes_credential(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.post(self.url, {"remove_credential": ""}, follow=True)
        self.assertRedirects(r, "/accounts/profile/")
        self.assertContains(r, "Removed security key <strong>Alices Key</strong>")

        self.assertFalse(self.alice.credentials.exists())

    def test_it_checks_owner(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.post(self.url, {"remove_credential": ""})
        self.assertEqual(r.status_code, 400)
