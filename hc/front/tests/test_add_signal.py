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
            "phone": "+1234567890",
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
        form = {"phone": "+1234567890", "up": True}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertFalse(c.phone.notify_down)
        self.assertTrue(c.phone.notify_up)

    def test_it_rejects_unchecked_up_and_down(self) -> None:
        form = {"phone": "+1234567890"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Please select at least one.")
