from hc.accounts.models import Project
from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class SwitchChannelTestCase(BaseTestCase):
    def setUp(self):
        super(SwitchChannelTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project)

        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

        self.url = "/checks/%s/channels/%s/enabled" % (
            self.check.code,
            self.channel.code,
        )

    def test_it_enables(self):
        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, {"state": "on"})

        self.assertTrue(self.channel in self.check.channel_set.all())

    def test_it_disables(self):
        self.check.channel_set.add(self.channel)

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, {"state": "off"})

        self.assertFalse(self.channel in self.check.channel_set.all())

    def test_it_checks_ownership(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, {"state": "on"})
        self.assertEqual(r.status_code, 404)

    def test_it_checks_channels_ownership(self):
        charlies_project = Project.objects.create(owner=self.charlie)
        cc = Check.objects.create(project=charlies_project)

        # Charlie will try to assign Alice's channel to his check:
        self.url = "/checks/%s/channels/%s/enabled" % (cc.code, self.channel.code)

        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, {"state": "on"})
        self.assertEqual(r.status_code, 400)

    def test_it_allows_cross_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {"state": "on"})
        self.assertEqual(r.status_code, 200)
