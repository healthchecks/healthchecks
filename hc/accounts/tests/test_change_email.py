from __future__ import annotations

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test.utils import override_settings

from hc.test import BaseTestCase


class ChangeEmailTestCase(BaseTestCase):
    def get_html(self, email: EmailMessage) -> str:
        assert isinstance(email, EmailMultiAlternatives)
        html, _ = email.alternatives[0]
        assert isinstance(html, str)
        return html

    def test_it_requires_sudo_mode(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/change_email/")
        self.assertContains(r, "We have sent a confirmation code")

    def test_it_shows_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        r = self.client.get("/accounts/change_email/")
        self.assertContains(r, "Change Account's Email Address")

    @override_settings(SITE_ROOT="http://testserver", SESSION_COOKIE_SECURE=False)
    def test_it_sends_link(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"email": "alice2@example.org"}
        r = self.client.post("/accounts/change_email/", payload, follow=True)
        self.assertRedirects(r, "/accounts/change_email/")
        self.assertContains(r, "One Last Step")

        self.assertEqual(self.client.cookies["auto-login"].value, "1")
        self.assertEqual(self.client.cookies["auto-login"]["samesite"], "Lax")
        self.assertTrue(self.client.cookies["auto-login"]["httponly"])
        self.assertFalse(self.client.cookies["auto-login"]["secure"])

        # The email address should have not changed yet
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice@example.org")
        self.assertTrue(self.alice.has_usable_password())

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, f"Log in to {settings.SITE_NAME}")
        html = self.get_html(message)
        self.assertIn("http://testserver/accounts/change_email/", html)

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_it_sets_secure_autologin_cookie(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"email": "alice2@example.org"}
        r = self.client.post("/accounts/change_email/", payload)
        self.assertTrue(r.cookies["auto-login"]["secure"])

    def test_it_requires_unique_email(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.set_sudo_flag()

        payload = {"email": "bob@example.org"}
        r = self.client.post("/accounts/change_email/", payload)
        self.assertContains(r, "bob@example.org is already registered")

        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice@example.org")
