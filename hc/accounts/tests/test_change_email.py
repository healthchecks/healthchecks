from hc.test import BaseTestCase


class ChangeEmailTestCase(BaseTestCase):
    def test_it_requires_sudo_mode(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/change_email/")
        self.assertContains(r, "We have sent a confirmation code")

    def test_it_shows_form(self):
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get("/accounts/change_email/")
        self.assertContains(r, "Change Account's Email Address")

    def test_it_updates_email(self):
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"email": "alice2@example.org"}
        r = self.client.post("/accounts/change_email/", payload, follow=True)
        self.assertRedirects(r, "/accounts/change_email/done/")
        self.assertContains(r, "Email Address Updated")

        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice2@example.org")
        self.assertFalse(self.alice.has_usable_password())

        # The user should have been logged out:
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_it_requires_unique_email(self):
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"email": "bob@example.org"}
        r = self.client.post("/accounts/change_email/", payload)
        self.assertContains(r, "bob@example.org is already registered")

        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice@example.org")
