from __future__ import annotations

from django.test.utils import override_settings

from hc.test import BaseTestCase


class SignupCsrfTestCase(BaseTestCase):
    def test_it_works(self):
        r = self.client.get("/accounts/signup/csrf/")
        self.assertTrue(r.cookies["csrftoken"])

    def test_it_requires_unauthenticated_user(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/signup/csrf/")
        self.assertEqual(r.status_code, 403)

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_requires_registration_open(self):
        r = self.client.get("/accounts/signup/csrf/")
        self.assertEqual(r.status_code, 403)
