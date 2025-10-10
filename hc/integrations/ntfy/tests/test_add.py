from __future__ import annotations

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class AddNtfyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/projects/{self.project.code}/add_ntfy/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "simple HTTP-based pub-sub")

    def test_it_creates_channel(self) -> None:
        form = {
            "topic": "foo",
            "url": "https://example.org",
            "priority": "5",
            "priority_up": "1",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "ntfy")
        self.assertEqual(c.ntfy.topic, "foo")
        self.assertEqual(c.ntfy.url, "https://example.org")
        self.assertEqual(c.ntfy.priority, 5)
        self.assertEqual(c.ntfy.priority_up, 1)
        self.assertEqual(c.project, self.project)

        # Make sure it calls assign_all_checks
        self.assertEqual(c.checks.count(), 1)

    def test_it_requires_topic(self) -> None:
        form = {
            "url": "https://example.org",
            "priority": "5",
            "priority_up": "1",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "This field is required")

    def test_it_validates_url(self) -> None:
        form = {
            "topic": "foo",
            "url": "this is not an url",
            "priority": "5",
            "priority_up": "1",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Enter a valid URL")

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_saves_token(self) -> None:
        form = {
            "topic": "foo",
            "url": "https://example.org",
            "priority": "5",
            "priority_up": "1",
            "token": "tk_test",
        }

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.ntfy.token, "tk_test")
