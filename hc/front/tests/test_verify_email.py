from __future__ import annotations

from hc.api.models import Channel
from hc.test import BaseTestCase


class VerifyEmailTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

    def test_it_works(self) -> None:
        token = self.channel.make_token()
        url = "/integrations/%s/verify/%s/" % (self.channel.code, token)

        r = self.client.get(url)
        assert r.status_code == 200, r.status_code

        channel = Channel.objects.get(code=self.channel.code)
        assert channel.email_verified

    def test_it_handles_bad_token(self) -> None:
        url = "/integrations/%s/verify/bad-token/" % self.channel.code

        r = self.client.get(url)
        assert r.status_code == 200, r.status_code

        channel = Channel.objects.get(code=self.channel.code)
        assert not channel.email_verified

    def test_missing_channel(self) -> None:
        # Valid UUID, and even valid token but there is no channel for it:
        code = "6837d6ec-fc08-4da5-a67f-08a9ed1ccf62"
        token = self.channel.make_token()
        url = "/integrations/%s/verify/%s/" % (code, token)

        r = self.client.get(url)
        assert r.status_code == 404
