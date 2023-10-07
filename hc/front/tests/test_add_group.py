from __future__ import annotations

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class AddGroupTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/projects/{self.project.code}/add_group/"

        self.c1 = Channel.objects.create(project=self.project, kind="email")
        self.c1_code_str = str(self.c1.code)

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

    def test_it_creates_channel(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        form = {"label": "My Group", "channels": self.c1_code_str}
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get(kind="group")
        self.assertEqual(list(c.group_channels), [self.c1])
        self.assertEqual(c.name, "My Group")

        # Make sure it calls assign_all_checks
        self.assertEqual(c.checks.count(), 1)

    def test_it_rejects_nonexistent_channel_code(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        form = {"channels": "b1a1a6b0-7b69-4c30-8d01-63cf6e85a372"}
        r = self.client.post(self.url, form)

        # It should show an error message
        self.assertContains(r, "Select a valid choice", status_code=200)
        # It should not create a group integration
        self.assertFalse(Channel.objects.filter(kind="group").exists())

    def test_it_rejects_another_projects_channel(self) -> None:
        # c1 now belongs to Bob:
        self.c1.project = self.bobs_project
        self.c1.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"channels": self.c1_code_str})

        # It should show an error message
        self.assertContains(r, "Select a valid choice", status_code=200)
        # It should not create a group integration
        self.assertFalse(Channel.objects.filter(kind="group").exists())
