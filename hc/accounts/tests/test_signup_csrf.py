from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(REGISTRATION_OPEN=True)
class SignupCsrfTestCase(BaseTestCase):
    def test_it_works(self) -> None:
        r = self.client.get("/accounts/signup/csrf/")
        self.assertTrue(r.cookies["csrftoken"])

    def test_it_requires_unauthenticated_user(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/signup/csrf/")
        self.assertEqual(r.status_code, 403)

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_requires_registration_open(self) -> None:
        r = self.client.get("/accounts/signup/csrf/")
        self.assertEqual(r.status_code, 403)
