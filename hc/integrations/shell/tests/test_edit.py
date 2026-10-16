from __future__ import annotations

import json

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class EditShellTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check.objects.create(project=self.project)

        definition = {
            "cmd_up": "logger up",
            "cmd_down": "logger down",
        }

        self.channel = Channel(project=self.project, kind="shell")
        self.channel.value = json.dumps(definition)
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/edit/"

    def test_it_shows_form(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Shell Command Settings")

        self.assertContains(r, "logger up")
        self.assertContains(r, "logger down")

    def test_it_saves_form_and_redirects(self) -> None:
        form = {
            "cmd_up": "logger UP",
            "cmd_down": "logger DOWN",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.shell.cmd_up, "logger UP")
        self.assertEqual(self.channel.shell.cmd_down, "logger DOWN")

        # Make sure it does not call assign_all_checks
        self.assertFalse(self.channel.checks.exists())

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {})
        self.assertEqual(r.status_code, 403)
