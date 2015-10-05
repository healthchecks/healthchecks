from django.contrib.auth.models import User
from django.test import TestCase

from hc.api.models import Channel


class ChannelChecksTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.channel = Channel(user=self.alice, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

    def test_it_works(self):
        url = "/integrations/%s/checks/" % self.channel.code

        self.client.login(username="alice", password="password")
        r = self.client.get(url)
        self.assertContains(r, "alice@example.org", status_code=200)

    def test_it_checks_owner(self):
        mallory = User(username="mallory")
        mallory.set_password("password")
        mallory.save()

        # channel does not belong to mallory so this should come back
        # with 403 Forbidden:
        url = "/integrations/%s/checks/" % self.channel.code
        self.client.login(username="mallory", password="password")
        r = self.client.get(url)
        assert r.status_code == 403

    def test_missing_channel(self):
        # Valid UUID but there is no channel for it:
        url = "/integrations/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/checks/"

        self.client.login(username="alice", password="password")
        r = self.client.get(url)
        assert r.status_code == 404
