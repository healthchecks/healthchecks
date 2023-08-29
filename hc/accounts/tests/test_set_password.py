from __future__ import annotations

from hc.test import BaseTestCase


class SetPasswordTestCase(BaseTestCase):
    def test_it_requires_sudo_mode(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/set_password/")
        self.assertContains(r, "We have sent a confirmation code")

    def test_it_shows_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get("/accounts/set_password/")
        self.assertContains(r, "Please pick a password")

    def test_it_sets_password(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"password": "correct horse battery staple"}
        r = self.client.post("/accounts/set_password/", payload)
        self.assertRedirects(r, "/accounts/profile/")

        old_password = self.alice.password
        self.alice.refresh_from_db()
        self.assertNotEqual(self.alice.password, old_password)

    def test_post_checks_length(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"password": "abc"}
        r = self.client.post("/accounts/set_password/", payload)
        self.assertEqual(r.status_code, 200)

        old_password = self.alice.password
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.password, old_password)
