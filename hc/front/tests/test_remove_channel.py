from django.contrib.auth.models import User
from django.test import TestCase
from hc.api.models import Channel


class RemoveChannelTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.channel = Channel(user=self.alice, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

    def test_it_works(self):
        url = "/integrations/%s/remove/" % self.channel.code

        self.client.login(username="alice", password="password")
        r = self.client.post(url)
        assert r.status_code == 302

        assert Channel.objects.count() == 0

    def test_it_handles_bad_uuid(self):
        url = "/integrations/not-uuid/remove/"

        self.client.login(username="alice", password="password")
        r = self.client.post(url)
        assert r.status_code == 400

    def test_it_checks_owner(self):
        url = "/integrations/%s/remove/" % self.channel.code

        mallory = User(username="mallory")
        mallory.set_password("password")
        mallory.save()

        self.client.login(username="mallory", password="password")
        r = self.client.post(url)
        assert r.status_code == 403

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no channel for it:
        url = "/integrations/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/remove/"

        self.client.login(username="alice", password="password")
        r = self.client.post(url)
        assert r.status_code == 404
