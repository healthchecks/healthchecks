from __future__ import annotations

from hc.accounts.models import Project
from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class UpdateChannelTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.channel = Channel.objects.create(project=self.project, kind="email")

    def test_it_works(self) -> None:
        payload = {"channel": self.channel.code, "check-%s" % self.check.code: True}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.channels_url, data=payload)
        self.assertRedirects(r, self.channels_url)

        channel = Channel.objects.get(code=self.channel.code)
        checks = channel.checks.all()
        assert len(checks) == 1
        assert checks[0].code == self.check.code

    def test_team_access_works(self) -> None:
        payload = {"channel": self.channel.code, "check-%s" % self.check.code: True}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.channels_url, data=payload, follow=True)
        self.assertEqual(r.status_code, 200)

    def test_it_checks_channel_user(self) -> None:
        charlies_project = Project.objects.create(owner=self.charlie)
        url = f"/projects/{charlies_project.code}/integrations/"

        payload = {"channel": self.channel.code}
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(url, data=payload)

        # self.channel does not belong to charlie, this should fail--
        self.assertEqual(r.status_code, 403)

    def test_it_checks_check_owner(self) -> None:
        charlies_project = Project.objects.create(owner=self.charlie)
        url = f"/projects/{charlies_project.code}/integrations/"

        charlies_channel = Channel(project=charlies_project, kind="email")
        charlies_channel.value = "charlie@example.org"
        charlies_channel.save()

        payload = {"channel": charlies_channel.code, "check-%s" % self.check.code: True}
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(url, data=payload)

        # charlies_channel belongs to charlie but self.check does not--
        self.assertEqual(r.status_code, 403)

    def test_it_handles_missing_channel(self) -> None:
        # Correct UUID but there is no channel for it:
        payload = {"channel": "6837d6ec-fc08-4da5-a67f-08a9ed1ccf62"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.channels_url, data=payload)
        self.assertEqual(r.status_code, 400)

    def test_it_handles_missing_check(self) -> None:
        # check- key has a correct UUID but there's no check object for it
        payload = {
            "channel": self.channel.code,
            "check-6837d6ec-fc08-4da5-a67f-08a9ed1ccf62": True,
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.channels_url, data=payload)
        self.assertEqual(r.status_code, 400)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        payload = {"channel": self.channel.code}

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.channels_url, data=payload)
        self.assertEqual(r.status_code, 403)
