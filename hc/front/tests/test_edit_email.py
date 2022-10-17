from __future__ import annotations

import json

from django.core import mail
from django.test.utils import override_settings

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class EditEmailTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check.objects.create(project=self.project)

        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = json.dumps(
            {"value": "alerts@example.org", "up": True, "down": True}
        )
        self.channel.email_verified = True
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/edit/"

    def test_it_shows_form(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Get an email message when check goes up or down.")
        self.assertContains(r, "alerts@example.org")
        self.assertContains(r, "Email Settings")

    def test_it_saves_changes(self):
        form = {"value": "new@example.org", "down": "true", "up": "false"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.email_value, "new@example.org")
        self.assertTrue(self.channel.email_notify_down)
        self.assertFalse(self.channel.email_notify_up)

        # It should send a verification link
        email = mail.outbox[0]
        self.assertTrue(email.subject.startswith("Verify email address on"))
        self.assertEqual(email.to[0], "new@example.org")

        # Make sure it does not call assign_all_checks
        self.assertFalse(self.channel.checks.exists())

    def test_it_skips_verification_if_email_unchanged(self):
        form = {"value": "alerts@example.org", "down": "false", "up": "true"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.email_value, "alerts@example.org")
        self.assertFalse(self.channel.email_notify_down)
        self.assertTrue(self.channel.email_notify_up)
        self.assertTrue(self.channel.email_verified)

        # The email address did not change, so we should skip verification
        self.assertEqual(len(mail.outbox), 0)

    def test_team_access_works(self):
        form = {"value": "new@example.org", "down": "true", "up": "true"}

        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, form)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.email_value, "new@example.org")

    @override_settings(EMAIL_USE_VERIFICATION=False)
    def test_it_hides_confirmation_needed_notice(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertNotContains(r, "Requires confirmation")

    @override_settings(EMAIL_USE_VERIFICATION=False)
    def test_it_auto_verifies_email(self):
        form = {"value": "dan@example.org", "down": "true", "up": "true"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.email_value, "dan@example.org")

        # Email should *not* have been sent
        self.assertEqual(len(mail.outbox), 0)

    def test_it_auto_verifies_own_email(self):
        form = {"value": "alice@example.org", "down": "true", "up": "true"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.email_value, "alice@example.org")

        # Email should *not* have been sent
        self.assertEqual(len(mail.outbox), 0)

    def test_it_resets_disabled_flag(self):
        self.channel.disabled = True
        self.channel.save()

        form = {"value": "alice-fixed@example.org", "down": "true", "up": "true"}
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertFalse(self.channel.disabled)
        self.assertFalse(self.channel.email_verified)

        # It should send a verification link
        email = mail.outbox[0]
        self.assertTrue(email.subject.startswith("Verify email address on"))

    def test_it_requires_rw_access(self):
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
