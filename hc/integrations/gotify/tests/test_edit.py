from __future__ import annotations

import json

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class EditGotifyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        self.channel = Channel(project=self.project, kind="gotify")
        self.channel.value = json.dumps(
            {
                "url": "https://example.org",
                "token": "test-token",
                "priority": 5,
                "priority_up": 5,
            }
        )
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/edit/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Save Integration")
        self.assertContains(r, "https://example.org")
        self.assertContains(r, "test-token")

    def test_it_updates_channel(self) -> None:
        form = {
            "url": "https://example.com",
            "token": "updated-token",
            "priority": "9",
            "priority_up": "2",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.gotify.url, "https://example.com")
        self.assertEqual(self.channel.gotify.token, "updated-token")
        self.assertEqual(self.channel.gotify.priority, 9)
        self.assertEqual(self.channel.gotify.priority_up, 2)

        # Make sure it does not call assign_all_checks
        self.assertFalse(self.channel.checks.exists())

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
