from __future__ import annotations

import time
from unittest.mock import Mock, patch

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(RP_ID="testserver")
class LoginWebAuthnTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        # This is the user we're trying to authenticate
        session = self.client.session
        session["2fa_user"] = [self.alice.id, self.alice.email, (time.time()) + 300]
        session.save()

        self.url = "/accounts/login/two_factor/"
        self.checks_url = f"/projects/{self.project.code}/checks/"

    def test_it_shows_form(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(r, "Waiting for security key")
        self.assertNotContains(r, "Use authenticator app")

        # It should put a "state" key in the session:
        self.assertIn("state", self.client.session)

    def test_it_shows_totp_option(self) -> None:
        self.profile.totp = "0" * 32
        self.profile.save()

        r = self.client.get(self.url)
        self.assertContains(r, "Use authenticator app")

    def test_it_preserves_next_parameter_in_totp_url(self) -> None:
        self.profile.totp = "0" * 32
        self.profile.save()

        url = self.url + "?next=" + self.channels_url
        r = self.client.get(url)
        self.assertContains(r, "/login/two_factor/totp/?next=" + self.channels_url)

    def test_it_requires_unauthenticated_user(self) -> None:
        self.client.login(username="alice@example.org", password="password")

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

    @override_settings(RP_ID=None)
    def test_it_requires_rp_id(self) -> None:
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    @patch("hc.accounts.views.GetHelper.verify")
    def test_it_logs_in(self, mock_verify: Mock) -> None:
        mock_verify.return_value = True

        session = self.client.session
        session["state"] = "dummy-state"
        session.save()

        r = self.client.post(self.url, {"response": "dummy response"})
        self.assertRedirects(r, self.checks_url)

        self.assertNotIn("state", self.client.session)
        self.assertNotIn("2fa_user_id", self.client.session)

    @patch("hc.accounts.views.GetHelper.verify")
    def test_it_redirects_after_login(self, mock_verify: Mock) -> None:
        mock_verify.return_value = True

        session = self.client.session
        session["state"] = "dummy-state"
        session.save()

        url = self.url + "?next=" + self.channels_url
        r = self.client.post(url, {"response": "dummy response"})
        self.assertRedirects(r, self.channels_url)

    def test_it_handles_bad_json(self) -> None:
        session = self.client.session
        session["state"] = "dummy-state"
        session.save()

        r = self.client.post(self.url, {"response": "this is not json"})
        self.assertEqual(r.status_code, 400)

    @patch("hc.accounts.views.GetHelper.verify")
    def test_it_handles_authentication_failure(self, mock_verify: Mock) -> None:
        mock_verify.return_value = False

        session = self.client.session
        session["state"] = "dummy-state"
        session.save()

        r = self.client.post(self.url, {"response": "this is not json"})
        self.assertEqual(r.status_code, 400)
