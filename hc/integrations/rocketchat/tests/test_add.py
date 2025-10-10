from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


class AddRocketChatTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_rocketchat/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Integration Settings", status_code=200)
        self.assertNotContains(
            r, "click on <strong>Add Integration</strong>", status_code=200
        )

    def test_it_works(self) -> None:
        form = {"value": "http://example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "rocketchat")
        self.assertEqual(c.value, "http://example.org")
        self.assertEqual(c.project, self.project)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(ROCKETCHAT_ENABLED=False)
    def test_it_handles_disabled_integration(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
