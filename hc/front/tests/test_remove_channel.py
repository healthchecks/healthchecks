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
        url = "/channels/%s/remove/" % self.channel.code

        self.client.login(username="alice", password="password")
        r = self.client.post(url)
        assert r.status_code == 302

        assert Channel.objects.count() == 0

    def test_it_handles_bad_uuid(self):
        url = "/channels/not-uuid/remove/"

        self.client.login(username="alice", password="password")
        r = self.client.post(url)
        assert r.status_code == 400

    def test_it_checks_owner(self):
        url = "/channels/%s/remove/" % self.channel.code

        mallory = User(username="mallory")
        mallory.set_password("password")
        mallory.save()

        self.client.login(username="mallory", password="password")
        r = self.client.post(url)
        assert r.status_code == 403
