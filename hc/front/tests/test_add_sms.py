from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


@override_settings(TWILIO_ACCOUNT="foo", TWILIO_AUTH="foo", TWILIO_FROM="123")
class AddSmsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/projects/{self.project.code}/add_sms/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Add SMS Integration")
        self.assertContains(r, "Get a SMS message")

    @override_settings(USE_PAYMENTS=True)
    def test_it_warns_about_limits(self):
        self.profile.sms_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "upgrade to a")

    def test_it_creates_channel(self):
        form = {"label": "My Phone", "phone": "+1234567890", "down": True}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "sms")
        self.assertEqual(c.phone_number, "+1234567890")
        self.assertEqual(c.name, "My Phone")
        self.assertTrue(c.sms_notify_down)
        self.assertFalse(c.sms_notify_up)
        self.assertEqual(c.project, self.project)

        # Make sure it calls assign_all_checks
        self.assertEqual(c.checks.count(), 1)

    def test_it_rejects_bad_number(self):
        for v in ["not a phone number", False, 15, "+123456789A"]:
            form = {"phone": v}
            self.client.login(username="alice@example.org", password="password")
            r = self.client.post(self.url, form)
            self.assertContains(r, "Invalid phone number format.")

    def test_it_trims_whitespace(self):
        form = {"phone": "   +1234567890   ", "down": True}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.phone_number, "+1234567890")

    @override_settings(TWILIO_AUTH=None)
    def test_it_requires_credentials(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self):
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_strips_invisible_formatting_characters(self):
        form = {"phone": "\u202c+1234567890\u202c", "down": True}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.phone_number, "+1234567890")

    def test_it_strips_hyphens(self):
        form = {"phone": "+123-4567890", "down": True}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.phone_number, "+1234567890")

    def test_it_strips_spaces(self):
        form = {"phone": "+123 45 678 90", "down": True}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.phone_number, "+1234567890")

    def test_it_handles_down_false_up_true(self):
        form = {"phone": "+1234567890", "up": True}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertFalse(c.sms_notify_down)
        self.assertTrue(c.sms_notify_up)

    def test_it_rejects_unchecked_up_and_down(self):
        form = {"phone": "+1234567890"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Please select at least one.")
