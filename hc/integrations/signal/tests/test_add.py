from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


@override_settings(SIGNAL_CLI_SOCKET="/tmp/dummy-signal-cli-socket")
class AddSignalTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/projects/{self.project.code}/add_signal/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Add Signal Integration")
        self.assertContains(r, "Get a Signal message")

    def test_it_creates_channel(self) -> None:
        form = {
            "label": "My Phone",
            "recipient": "+1234567890",
            "down": "true",
            "up": "true",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "signal")
        self.assertEqual(c.phone.value, "+1234567890")
        self.assertEqual(c.name, "My Phone")
        self.assertTrue(c.phone.notify_down)
        self.assertTrue(c.phone.notify_up)
        self.assertEqual(c.project, self.project)

        # Make sure it calls assign_all_checks
        self.assertEqual(c.checks.count(), 1)

    def test_it_handles_username(self) -> None:
        form = {
            "label": "My Phone",
            "recipient": "foobar.123",
            "down": "true",
            "up": "true",
        }

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.phone.value, "foobar.123")

    @override_settings(SIGNAL_CLI_SOCKET=None)
    def test_it_handles_disabled_integration(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_handles_down_false_up_true(self) -> None:
        form = {"recipient": "+1234567890", "up": True}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertFalse(c.phone.notify_down)
        self.assertTrue(c.phone.notify_up)

    def test_it_rejects_unchecked_up_and_down(self) -> None:
        form = {"recipient": "+1234567890"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Please select at least one.")

    def test_it_rejects_bad_phone(self) -> None:
        for v in ["not a phone number", False, 15, "+123456789A"]:
            self.client.login(username="alice@example.org", password="password")
            r = self.client.post(self.url, {"recipient": v})
            self.assertContains(r, "Invalid phone number format.")

    def test_it_rejects_bad_username(self) -> None:
        for v in ["a.123", "foobar.0"]:
            self.client.login(username="alice@example.org", password="password")
            r = self.client.post(self.url, {"recipient": v})
            self.assertContains(r, "Invalid username format.")

    def test_it_strips_invisible_formatting_characters(self) -> None:
        form = {"recipient": "\u202c+1234567890\u202c", "down": True}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.phone.value, "+1234567890")

    def test_it_strips_hyphens(self) -> None:
        form = {"recipient": "+123-4567890", "down": True}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.phone.value, "+1234567890")

    def test_it_strips_spaces(self) -> None:
        form = {"recipient": "   +123 45 678 90   ", "down": True}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.phone.value, "+1234567890")
