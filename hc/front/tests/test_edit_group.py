from __future__ import annotations

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class EditGroupTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        self.c1 = Channel.objects.create(project=self.project, kind="email")
        self.c1_code_str = str(self.c1.code)

        self.channel = Channel(project=self.project, kind="group")
        self.channel.value = self.c1_code_str
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/edit/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "multiple integrations at once.")
        self.assertContains(r, self.c1_code_str)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_handles_nonexistent_members_in_value_field(self) -> None:
        # value references a channel that does not exist. The "edit group"
        # should be able to cope with this and just ignore the invalid UUID.
        self.channel.value = "7d65be92-8763-4acd-95bb-a457115d1557"
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, self.c1_code_str)
        self.assertNotContains(r, "7d65be92-8763-4acd-95bb-a457115d1557")

    def test_it_updates_channel(self) -> None:
        c2 = Channel.objects.create(project=self.project, kind="email")

        self.client.login(username="alice@example.org", password="password")
        form = {"label": "New Name", "channels": f"{c2.code}"}
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.name, "New Name")
        self.assertEqual(list(self.channel.group_channels), [c2])

        # Make sure it does not call assign_all_checks
        self.assertFalse(self.channel.checks.exists())
