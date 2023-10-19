from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth.models import User

from hc.api.models import Check
from hc.payments.models import Subscription
from hc.test import BaseTestCase


class CloseAccountTestCase(BaseTestCase):
    def test_it_requires_sudo_mode(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/close/")
        self.assertContains(r, "We have sent a confirmation code")

    def test_it_shows_confirmation_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get("/accounts/close/")
        self.assertContains(r, "Close Account?")
        self.assertContains(r, "1 project")
        self.assertContains(r, "0 checks")

    def test_it_works(self) -> None:
        Check.objects.create(project=self.project, tags="foo a-B_1  baz@")
        Subscription.objects.create(
            user=self.alice, subscription_id="123", customer_id="fake-customer-id"
        )

        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"confirmation": "alice@example.org"}
        r = self.client.post("/accounts/close/", payload, follow=True)
        self.assertRedirects(r, "/accounts/login/")
        self.assertContains(r, "Account closed.")

        # Alice should be gone
        alices = User.objects.filter(username="alice")
        self.assertFalse(alices.exists())

        # Check should be gone
        self.assertFalse(Check.objects.exists())

        # Subscription should be gone
        self.assertFalse(Subscription.objects.exists())

    def test_it_requires_confirmation(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"confirmation": "incorrect"}
        r = self.client.post("/accounts/close/", payload)
        self.assertContains(r, "Close Account?")
        self.assertContains(r, "has-error")

        # Alice should be still present
        self.alice.refresh_from_db()
        self.profile.refresh_from_db()

    def test_partner_removal_works(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        self.set_sudo_flag()

        payload = {"confirmation": "bob@example.org"}
        r = self.client.post("/accounts/close/", payload)
        self.assertRedirects(r, "/accounts/login/")

        # Alice should be still present
        self.alice.refresh_from_db()
        self.profile.refresh_from_db()

        # Bob should be gone
        bobs = User.objects.filter(username="bob")
        self.assertFalse(bobs.exists())
