from __future__ import annotations

from django.test import TestCase
from django.test.utils import override_settings


class BasicsTestCase(TestCase):
    @override_settings(DEBUG=False, SECRET_KEY="abc")
    def test_it_redirects_to_login(self) -> None:
        r = self.client.get("/")
        self.assertRedirects(r, "/accounts/login/")

    @override_settings(DEBUG=False, SECRET_KEY="abc")
    def test_it_shows_no_warning(self) -> None:
        r = self.client.get("/accounts/login/")
        self.assertContains(r, "Sign In to", status_code=200)
        self.assertNotContains(r, "do not use in production")

    @override_settings(DEBUG=True, SECRET_KEY="abc")
    def test_it_shows_debug_warning(self) -> None:
        r = self.client.get("/accounts/login/")
        self.assertContains(r, "Running in debug mode")

    @override_settings(DEBUG=False, SECRET_KEY="---")
    def test_it_shows_secret_key_warning(self) -> None:
        r = self.client.get("/accounts/login/")
        self.assertContains(r, "Sign In to", status_code=200)
        self.assertContains(r, "Running with an insecure SECRET_KEY value")

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_obeys_registration_open(self) -> None:
        r = self.client.get("/accounts/login/")

        self.assertNotContains(r, "Sign Up")
