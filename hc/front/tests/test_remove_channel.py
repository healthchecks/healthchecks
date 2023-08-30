from __future__ import annotations

from hc.api.models import Channel
from hc.test import BaseTestCase


class RemoveChannelTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/remove/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.channels_url)

        assert Channel.objects.count() == 0

    def test_team_access_works(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url)
        assert Channel.objects.count() == 0

    def test_it_handles_bad_uuid(self) -> None:
        url = "/integrations/not-uuid/remove/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertEqual(r.status_code, 404)

    def test_it_checks_owner(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self) -> None:
        # Valid UUID but there is no channel for it:
        url = "/integrations/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/remove/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)
