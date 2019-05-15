from django.contrib.auth.hashers import make_password

from hc.test import BaseTestCase


class ChangeEmailTestCase(BaseTestCase):
    def test_it_shows_form(self):
        self.profile.token = make_password("foo", "change-email")
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/change_email/foo/")
        self.assertContains(r, "Change Account's Email Address")

    def test_it_changes_password(self):
        self.profile.token = make_password("foo", "change-email")
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        payload = {"email": "alice2@example.org"}
        self.client.post("/accounts/change_email/foo/", payload)

        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice2@example.org")
        self.assertFalse(self.alice.has_usable_password())

    def test_it_requires_unique_email(self):
        self.profile.token = make_password("foo", "change-email")
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        payload = {"email": "bob@example.org"}
        r = self.client.post("/accounts/change_email/foo/", payload)
        self.assertContains(r, "bob@example.org is already registered")

        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice@example.org")
