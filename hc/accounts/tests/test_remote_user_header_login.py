from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(
    REMOTE_USER_HEADER="AUTH_USER",
    AUTHENTICATION_BACKENDS=("hc.accounts.backends.CustomHeaderBackend",),
)
class RemoteUserHeaderTestCase(BaseTestCase):
    @override_settings(REMOTE_USER_HEADER=None)
    def test_it_does_nothing_when_not_configured(self) -> None:
        r = self.client.get("/accounts/profile/", AUTH_USER="alice@example.org")
        self.assertRedirects(r, "/accounts/login/?next=/accounts/profile/")

    def test_it_logs_user_in(self) -> None:
        r = self.client.get("/accounts/profile/", AUTH_USER="alice@example.org")
        self.assertContains(r, "alice@example.org")

    def test_it_does_nothing_when_header_not_set(self) -> None:
        r = self.client.get("/accounts/profile/")
        self.assertRedirects(r, "/accounts/login/?next=/accounts/profile/")

    def test_it_does_nothing_when_header_is_empty_string(self) -> None:
        r = self.client.get("/accounts/profile/", AUTH_USER="")
        self.assertRedirects(r, "/accounts/login/?next=/accounts/profile/")

    def test_it_creates_user(self) -> None:
        r = self.client.get("/accounts/profile/", AUTH_USER="dave@example.org")
        self.assertContains(r, "dave@example.org")

        q = User.objects.filter(email="dave@example.org")
        self.assertTrue(q.exists())

    def test_it_logs_out_another_user_when_header_is_empty_string(self) -> None:
        self.client.login(remote_user_email="bob@example.org")

        r = self.client.get("/accounts/profile/", AUTH_USER="")
        self.assertRedirects(r, "/accounts/login/?next=/accounts/profile/")

    def test_it_logs_out_another_user(self) -> None:
        self.client.login(remote_user_email="bob@example.org")

        r = self.client.get("/accounts/profile/", AUTH_USER="alice@example.org")
        self.assertContains(r, "alice@example.org")

    def test_it_handles_already_logged_in_user(self) -> None:
        self.client.login(remote_user_email="alice@example.org")

        with patch("hc.accounts.middleware.auth") as mock_auth:
            r = self.client.get("/accounts/profile/", AUTH_USER="alice@example.org")

            mock_auth.authenticate.assert_not_called()
            self.assertContains(r, "alice@example.org")
