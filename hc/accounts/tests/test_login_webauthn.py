from unittest.mock import patch

from django.test.utils import override_settings
from hc.test import BaseTestCase


@override_settings(RP_ID="testserver")
class LoginWebauthnTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        # This is the user we're trying to authenticate
        session = self.client.session
        session["2fa_user_id"] = self.alice.id
        session.save()

        self.url = "/accounts/login/two_factor/"
        self.checks_url = f"/projects/{self.project.code}/checks/"

    def test_it_shows_form(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Waiting for security key")

        # It should put a "state" key in the session:
        self.assertIn("state", self.client.session)

    @override_settings(RP_ID=None)
    def test_it_requires_rp_id(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 500)

    @patch("hc.accounts.views._check_credential")
    def test_it_logs_in(self, mock_check_credential):
        mock_check_credential.return_value = True

        session = self.client.session
        session["state"] = "dummy-state"
        session.save()

        payload = {
            "name": "My New Key",
            "credential_id": "e30=",
            "client_data_json": "e30=",
            "authenticator_data": "e30=",
            "signature": "e30=",
        }

        r = self.client.post(self.url, payload)
        self.assertRedirects(r, self.checks_url)

        self.assertNotIn("state", self.client.session)
        self.assertNotIn("2fa_user_id", self.client.session)

    @patch("hc.accounts.views._check_credential")
    def test_it_redirects_after_login(self, mock_check_credential):
        mock_check_credential.return_value = True

        session = self.client.session
        session["state"] = "dummy-state"
        session.save()

        payload = {
            "name": "My New Key",
            "credential_id": "e30=",
            "client_data_json": "e30=",
            "authenticator_data": "e30=",
            "signature": "e30=",
        }

        url = self.url + "?next=" + self.channels_url
        r = self.client.post(url, payload)
        self.assertRedirects(r, self.channels_url)

    @patch("hc.accounts.views._check_credential")
    def test_it_handles_bad_base64(self, mock_check_credential):
        mock_check_credential.return_value = None

        session = self.client.session
        session["state"] = "dummy-state"
        session.save()

        payload = {
            "name": "My New Key",
            "credential_id": "this is not base64 data",
            "client_data_json": "e30=",
            "authenticator_data": "e30=",
            "signature": "e30=",
        }

        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 400)

    @patch("hc.accounts.views._check_credential")
    def test_it_handles_authentication_failure(self, mock_check_credential):
        mock_check_credential.return_value = None

        session = self.client.session
        session["state"] = "dummy-state"
        session.save()

        payload = {
            "name": "My New Key",
            "credential_id": "e30=",
            "client_data_json": "e30=",
            "authenticator_data": "e30=",
            "signature": "e30=",
        }

        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 400)
