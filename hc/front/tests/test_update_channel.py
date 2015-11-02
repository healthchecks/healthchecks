from django.contrib.auth.models import User
from django.test import TestCase
from hc.api.models import Channel, Check


class UpdateChannelTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.check = Check(user=self.alice)
        self.check.save()

        self.channel = Channel(user=self.alice, kind="email")
        self.channel.email = "alice@example.org"
        self.channel.save()

    def test_it_works(self):
        payload = {
            "channel": self.channel.code,
            "check-%s" % self.check.code: True
        }

        self.client.login(username="alice", password="password")
        r = self.client.post("/integrations/", data=payload)
        assert r.status_code == 302

        channel = Channel.objects.get(code=self.channel.code)
        checks = channel.checks.all()
        assert len(checks) == 1
        assert checks[0].code == self.check.code

    def test_it_checks_channel_user(self):
        mallory = User(username="mallory")
        mallory.set_password("password")
        mallory.save()

        payload = {"channel": self.channel.code}

        self.client.login(username="mallory", password="password")
        r = self.client.post("/integrations/", data=payload)

        # self.channel does not belong to mallory, this should fail--
        assert r.status_code == 403

    def test_it_checks_check_user(self):
        mallory = User(username="mallory")
        mallory.set_password("password")
        mallory.save()

        mc = Channel(user=mallory, kind="email")
        mc.email = "mallory@example.org"
        mc.save()

        payload = {
            "channel": mc.code,
            "check-%s" % self.check.code: True
        }
        self.client.login(username="mallory", password="password")
        r = self.client.post("/integrations/", data=payload)

        # mc belongs to mallorym but self.check does not--
        assert r.status_code == 403

    def test_it_handles_missing_channel(self):
        # Correct UUID but there is no channel for it:
        payload = {"channel": "6837d6ec-fc08-4da5-a67f-08a9ed1ccf62"}

        self.client.login(username="alice", password="password")
        r = self.client.post("/integrations/", data=payload)
        assert r.status_code == 400

    def test_it_handles_missing_check(self):
        # check- key has a correct UUID but there's no check object for it
        payload = {
            "channel": self.channel.code,
            "check-6837d6ec-fc08-4da5-a67f-08a9ed1ccf62": True
        }

        self.client.login(username="alice", password="password")
        r = self.client.post("/integrations/", data=payload)
        assert r.status_code == 400
