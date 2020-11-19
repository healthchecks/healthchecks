from unittest.mock import patch

from django.test.utils import override_settings
from hc.test import BaseTestCase
from hc.accounts.models import Credential


@override_settings(RP_ID="testserver")
class AddCredentialTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.url = "/accounts/two_factor/add/"

    def test_it_requires_sudo_mode(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertContains(r, "We have sent a confirmation code")

    @override_settings(RP_ID=None)
    def test_it_requires_rp_id(self):
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_form(self):
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get(self.url)
        self.assertContains(r, "Add Security Key")

        # It should put a "state" key in the session:
        self.assertIn("state", self.client.session)

    @patch("hc.accounts.views._get_credential_data")
    def test_it_adds_credential(self, mock_get_credential_data):
        mock_get_credential_data.return_value = b"dummy-credential-data"

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

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

    def test_it_rejects_bad_base64(self):
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {
            "name": "My New Key",
            "client_data_json": "not valid base64",
            "attestation_object": "not valid base64",
        }

        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 400)

    def test_it_requires_client_data_json(self):
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {
            "name": "My New Key",
            "attestation_object": "e30=",
        }

        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 400)

    @patch("hc.accounts.views._get_credential_data")
    def test_it_handles_authentication_failure(self, mock_get_credential_data):
        mock_get_credential_data.return_value = None

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {
            "name": "My New Key",
            "client_data_json": "e30=",
            "attestation_object": "e30=",
        }

        r = self.client.post(self.url, payload, follow=True)
        self.assertEqual(r.status_code, 400)
