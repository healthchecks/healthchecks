from django.contrib.auth.models import User
from django.test import TestCase

from hc.api.models import Channel


class VerifyEmailTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.channel = Channel(user=self.alice, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

    def test_it_works(self):
        token = self.channel.make_token()
        url = "/channels/%s/verify/%s/" % (self.channel.code, token)

        r = self.client.post(url)
        assert r.status_code == 200, r.status_code

        channel = Channel.objects.get(code=self.channel.code)
        assert channel.email_verified

    def test_it_handles_bad_token(self):
        url = "/channels/%s/verify/bad-token/" % self.channel.code

        r = self.client.post(url)
        assert r.status_code == 200, r.status_code

        channel = Channel.objects.get(code=self.channel.code)
        assert not channel.email_verified

    def test_missing_channel(self):
        # Valid UUID, and even valid token but there is no channel for it:
        code = "6837d6ec-fc08-4da5-a67f-08a9ed1ccf62"
        token = self.channel.make_token()
        url = "/channels/%s/verify/%s/" % (code, token)

        r = self.client.post(url)
        assert r.status_code == 404
