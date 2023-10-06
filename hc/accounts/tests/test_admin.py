from __future__ import annotations

from hc.payments.models import Subscription
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

    def test_it_escapes_emails_when_showing_profiles(self) -> None:
        self.bob.email = "bob&friends@example.org"
        self.bob.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/admin/accounts/profile/")
        # The amperstand should be escaped
        self.assertNotContains(r, "bob&friends@example.org")

    def test_it_escapes_emails_when_showing_profiles_with_subscriptions(self) -> None:
        self.bob.email = "bob&friends@example.org"
        self.bob.save()

        self.sub = Subscription(user=self.bob)
        self.sub.plan_name = "Custom Plan"
        self.sub.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/admin/accounts/profile/")
        # The amperstand should be escaped
        self.assertNotContains(r, "bob&friends@example.org")
        self.assertContains(r, "<span>Custom Plan</span>")

    def test_it_shows_projects(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/admin/accounts/project/")
        self.assertContains(r, "Alices Project")
        self.assertContains(r, "Default Project for bob@example.org")

    def test_it_escapes_emails_when_showing_projects(self) -> None:
        self.bob.email = "bob&friends@example.org"
        self.bob.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/admin/accounts/project/")
        # The amperstand should be escaped
        self.assertNotContains(r, "bob&friends@example.org")
