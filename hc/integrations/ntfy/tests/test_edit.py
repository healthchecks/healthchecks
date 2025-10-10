from __future__ import annotations

import json

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class EditNtfyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        self.channel = Channel(project=self.project, kind="ntfy")
        self.channel.value = json.dumps(
            {
                "topic": "foo-bar-baz",
                "url": "https://example.org",
                "priority": 3,
                "priority_up": 0,
                "token": "test-token",
            }
        )
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/edit/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Save Integration")
        self.assertContains(r, "https://example.org")
        self.assertContains(r, "foo-bar-baz")
        self.assertContains(r, "test-token")

    def test_it_updates_channel(self) -> None:
        form = {
            "topic": "updated-topic",
            "url": "https://example.com",
            "priority": "4",
            "priority_up": "1",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.ntfy.topic, "updated-topic")
        self.assertEqual(self.channel.ntfy.url, "https://example.com")
        self.assertEqual(self.channel.ntfy.priority, 4)
        self.assertEqual(self.channel.ntfy.priority_up, 1)

        # Make sure it does not call assign_all_checks
        self.assertFalse(self.channel.checks.exists())

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_updates_token(self) -> None:
        form = {
            "topic": "updated-topic",
            "url": "https://example.com",
            "priority": "4",
            "priority_up": "1",
            "token": "tk_test",
        }

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.ntfy.token, "tk_test")
