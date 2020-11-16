from django.core.signing import TimestampSigner

from hc.test import BaseTestCase
from hc.accounts.models import Credential


class RemoveCredentialTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.c = Credential.objects.create(user=self.alice, name="Alices Key")
        self.url = f"/accounts/two_factor/{self.c.code}/remove/"

    def _set_sudo_flag(self):
        session = self.client.session
        session["sudo"] = TimestampSigner().sign("active")
        session.save()

    def test_it_shows_form(self):
        self.client.login(username="alice@example.org", password="password")
        self._set_sudo_flag()

        r = self.client.get(self.url)
        self.assertContains(r, "Remove Security Key")
        self.assertContains(r, "Alices Key")

    def test_it_removes_credential(self):
        self.client.login(username="alice@example.org", password="password")
        self._set_sudo_flag()

        r = self.client.post(self.url, {"remove_credential": ""}, follow=True)
        self.assertRedirects(r, "/accounts/profile/")
        self.assertContains(r, "Removed security key <strong>Alices Key</strong>")

        self.assertFalse(self.alice.credentials.exists())

    def test_it_checks_owner(self):
        self.client.login(username="charlie@example.org", password="password")
        self._set_sudo_flag()

        r = self.client.post(self.url, {"remove_credential": ""})
        self.assertEqual(r.status_code, 400)
