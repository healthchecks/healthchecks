from hc.api.models import Channel
from hc.test import BaseTestCase


class ChannelChecksTestCase(BaseTestCase):

    def setUp(self):
        super(ChannelChecksTestCase, self).setUp()
        self.channel = Channel(user=self.alice, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

    def test_it_works(self):
        url = "/integrations/%s/checks/" % self.channel.code

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertContains(r, "Assign Checks to Channel", status_code=200)

    def test_it_checks_owner(self):
        # channel does not belong to mallory so this should come back
        # with 403 Forbidden:
        url = "/integrations/%s/checks/" % self.channel.code
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(url)
        assert r.status_code == 403

    def test_missing_channel(self):
        # Valid UUID but there is no channel for it:
        url = "/integrations/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/checks/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        assert r.status_code == 404
