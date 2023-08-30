from __future__ import annotations

from hc.accounts.models import Project
from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class SwitchChannelTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

        self.url = f"/checks/{self.check.code}/channels/{self.channel.code}/enabled"

    def test_it_enables(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, {"state": "on"})

        self.assertTrue(self.channel in self.check.channel_set.all())

    def test_it_disables(self) -> None:
        self.check.channel_set.add(self.channel)

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, {"state": "off"})

        self.assertFalse(self.channel in self.check.channel_set.all())

    def test_it_checks_ownership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, {"state": "on"})
        self.assertEqual(r.status_code, 404)

    def test_it_checks_channels_ownership(self) -> None:
        charlies_project = Project.objects.create(owner=self.charlie)
        cc = Check.objects.create(project=charlies_project)

        # Charlie will try to assign Alice's channel to his check:
        self.url = f"/checks/{cc.code}/channels/{self.channel.code}/enabled"

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, {"state": "on"})
        self.assertEqual(r.status_code, 400)

    def test_it_allows_cross_team_access(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {"state": "on"})
        self.assertEqual(r.status_code, 200)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {"state": "on"})
        self.assertEqual(r.status_code, 403)
