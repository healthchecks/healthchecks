from __future__ import annotations

from django.contrib.auth.hashers import make_password
from django.core.signing import TimestampSigner

from hc.accounts.models import Credential
from hc.test import BaseTestCase


class CheckTokenTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.profile.token = make_password("secret-token", "login")
        self.profile.save()

        signed_token = TimestampSigner().sign("secret-token")
        self.url = f"/accounts/check_token/alice/{signed_token}/"
        self.checks_url = "/projects/%s/checks/" % self.project.code

    def test_it_shows_form(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(r, "You are about to log in")

    def test_it_redirects(self) -> None:
        r = self.client.post(self.url)

        self.assertRedirects(r, self.checks_url)

        # After login, token should be blank
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.token, "")

    def test_it_handles_email_in_username(self) -> None:
        # Healthchecks will generate usernames that look like UUIDs. But custom
        # authentication backends like django-auth-ldap can also create User objects
        # with non-UUID usernames. In this testcase we check if check_token works
        # with an username that looks like an email address.
        self.alice.username = "alice@example.org"
        self.alice.save()
        r = self.client.post(self.url.replace("alice", "alice@example.org"))
        self.assertRedirects(r, self.checks_url)

    def test_it_handles_get_with_cookie(self) -> None:
        self.client.cookies["auto-login"] = "1"
        r = self.client.get(self.url)
        self.assertRedirects(r, self.checks_url)

    def test_it_redirects_already_logged_in(self) -> None:
        # Login
        self.client.login(username="alice@example.org", password="password")

        # Login again, when already authenticated
        r = self.client.post(self.url)

        self.assertRedirects(r, self.checks_url)

    def test_it_redirects_bad_login(self) -> None:
        # Login with a bad token
        url = "/accounts/check_token/alice/invalid-token/"
        r = self.client.post(url, follow=True)
        self.assertRedirects(r, "/accounts/login/")
        self.assertContains(r, "incorrect or expired")

    def test_it_handles_next_parameter(self) -> None:
        url = self.url + "?next=" + self.channels_url
        r = self.client.post(url)
        self.assertRedirects(r, self.channels_url)

    def test_it_ignores_bad_next_parameter(self) -> None:
        url = self.url + "?next=/evil/"
        r = self.client.post(url)
        self.assertRedirects(r, self.checks_url)

    def test_it_redirects_to_webauthn_form(self) -> None:
        Credential.objects.create(user=self.alice, name="Alices Key")

        r = self.client.post(self.url)
        self.assertRedirects(
            r, "/accounts/login/two_factor/", fetch_redirect_response=False
        )

        # It should not log the user in yet
        self.assertNotIn("_auth_user_id", self.client.session)

        # Instead, it should set 2fa_user_id in the session
        user_id, email, valid_until = self.client.session["2fa_user"]
        self.assertEqual(user_id, self.alice.id)
