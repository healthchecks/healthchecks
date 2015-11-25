from django.contrib.auth.models import User
from django.test import TestCase
from hc.api.models import Channel


class AddChannelTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

    def test_it_works(self):
        url = "/integrations/add/"
        form = {"kind": "email", "value": "alice@example.org"}

        self.client.login(username="alice", password="password")
        r = self.client.post(url, form)

        assert r.status_code == 302
        assert Channel.objects.count() == 1

    def test_it_rejects_bad_kind(self):
        url = "/integrations/add/"
        form = {"kind": "dog", "value": "Lassie"}

        self.client.login(username="alice", password="password")
        r = self.client.post(url, form)

        assert r.status_code == 400, r.status_code

    def test_instructions_work(self):
        self.client.login(username="alice", password="password")
        for frag in ("email", "webhook", "pd", "pushover", "slack", "hipchat"):
            url = "/integrations/add_%s/" % frag
            r = self.client.get(url)
            self.assertContains(r, "Integration Settings", status_code=200)
