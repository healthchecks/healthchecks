from __future__ import annotations

from hc.api.models import Channel
from hc.test import BaseTestCase


class UpdateChannelNameTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.channel = Channel(kind="email", project=self.project)
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/name/"

    def test_it_works(self) -> None:
        payload = {"name": "My work email"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertRedirects(r, self.channels_url)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.name, "My work email")

    def test_team_access_works(self) -> None:
        payload = {"name": "Bob was here"}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, data=payload)

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.name, "Bob was here")

    def test_it_checks_ownership(self) -> None:
        payload = {"name": "Charlie Sent This"}

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self) -> None:
        # Valid UUID but there is no check for it:
        url = "/integrations/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/name/"
        payload = {"name": "Alice Was Here"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, data=payload)
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        payload = {"name": "My work email"}

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, data=payload)
        self.assertEqual(r.status_code, 403)
