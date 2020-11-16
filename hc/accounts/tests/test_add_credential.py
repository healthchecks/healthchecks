from unittest.mock import patch

from django.core.signing import TimestampSigner
from hc.test import BaseTestCase
from hc.accounts.models import Credential


class AddCredentialTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.url = "/accounts/two_factor/add/"

    def _set_sudo_flag(self):
        session = self.client.session
        session["sudo"] = TimestampSigner().sign("active")
        session.save()

    def test_it_requires_sudo_mode(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertContains(r, "We have sent a confirmation code")

    def test_it_shows_form(self):
        self.client.login(username="alice@example.org", password="password")
        self._set_sudo_flag()

        r = self.client.get(self.url)
        self.assertContains(r, "Add Security Key")

        # It should put a "state" key in the session:
        self.assertIn("state", self.client.session)

    @patch("hc.accounts.views._get_credential_data")
    def test_it_adds_credential(self, mock_get_credential_data):
        mock_get_credential_data.return_value = b"dummy-credential-data"

        self.client.login(username="alice@example.org", password="password")
        self._set_sudo_flag()

        payload = {
            "name": "My New Key",
            "client_data_json": "e30=",
            "attestation_object": "e30=",
        }

        r = self.client.post(self.url, payload, follow=True)
        self.assertRedirects(r, "/accounts/profile/")
        self.assertContains(r, "Added security key <strong>My New Key</strong>")

        c = Credential.objects.get()
        self.assertEqual(c.name, "My New Key")

    # FIXME: test authentication failure
