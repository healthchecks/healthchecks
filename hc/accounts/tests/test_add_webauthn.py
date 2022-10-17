from __future__ import annotations

from unittest.mock import patch

from django.test.utils import override_settings

from hc.accounts.models import Credential
from hc.test import BaseTestCase


@override_settings(RP_ID="testserver")
class AddWebauthnTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.url = "/accounts/two_factor/webauthn/"

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

    @patch("hc.accounts.views.CreateHelper.verify")
    def test_it_adds_credential(self, mock_verify):
        mock_verify.return_value = b"dummy-credential-data"

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        session = self.client.session
        session["state"] = "dummy state"
        session.save()

        payload = {"name": "My New Key", "response": "dummy response"}
        r = self.client.post(self.url, payload, follow=True)
        self.assertRedirects(r, "/accounts/profile/")
        self.assertContains(r, "Added security key <strong>My New Key</strong>")

        c = Credential.objects.get()
        self.assertEqual(c.name, "My New Key")

        # state should have been removed from the session
        self.assertNotIn("state", self.client.session)

    def test_it_handles_bad_response_json(self):
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        session = self.client.session
        session["state"] = "dummy state"
        session.save()

        payload = {"name": "My New Key", "response": "this is not json"}
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 400)

    @patch("hc.accounts.views.CreateHelper.verify")
    def test_it_handles_verification_failure(self, mock_verify):
        mock_verify.return_value = None

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        session = self.client.session
        session["state"] = "dummy state"
        session.save()

        payload = {"name": "My New Key", "response": "dummy response"}

        r = self.client.post(self.url, payload, follow=True)
        self.assertEqual(r.status_code, 400)
