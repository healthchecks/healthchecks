from __future__ import annotations

from hc.test import BaseTestCase


class AccountsAdminTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.alice.is_staff = True
        self.alice.is_superuser = True
        self.alice.save()

    def test_it_shows_profiles(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/admin/accounts/profile/")
        self.assertContains(r, "alice@example.org")
        self.assertContains(r, "bob@example.org")
