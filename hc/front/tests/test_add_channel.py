from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from hc.api.models import Channel


class AddChannelTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        settings.PUSHOVER_API_TOKEN = "bogus_token"
        settings.PUSHOVER_SUBSCRIPTION_URL = "bogus_url"

    def test_it_works(self):
        url = "/integrations/add/"
        form = {"kind": "email", "value": "alice@example.org"}

        self.client.login(username="alice", password="password")
        r = self.client.post(url, form)

        assert r.status_code == 302
        assert Channel.objects.count() == 1

    def test_it_trims_whitespace(self):
        """ Leading and trailing whitespace should get trimmed. """

        url = "/integrations/add/"
        form = {"kind": "email", "value": "   alice@example.org   "}

        self.client.login(username="alice", password="password")
        self.client.post(url, form)

        q = Channel.objects.filter(value="alice@example.org")
        self.assertEqual(q.count(), 1)

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

    def test_it_adds_pushover_channel(self):
        self.client.login(username="alice", password="password")

        session = self.client.session
        session["po_nonce"] = "n"
        session.save()

        params = "pushover_user_key=a&nonce=n&prio=0"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        assert r.status_code == 302

        channels = list(Channel.objects.all())
        assert len(channels) == 1
        assert channels[0].value == "a|0"

    def test_it_validates_pushover_priority(self):
        self.client.login(username="alice", password="password")

        session = self.client.session
        session["po_nonce"] = "n"
        session.save()

        params = "pushover_user_key=a&nonce=n&prio=abc"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        assert r.status_code == 400

    def test_it_validates_pushover_nonce(self):
        self.client.login(username="alice", password="password")

        session = self.client.session
        session["po_nonce"] = "n"
        session.save()

        params = "pushover_user_key=a&nonce=INVALID&prio=0"
        r = self.client.get("/integrations/add_pushover/?%s" % params)
        assert r.status_code == 403
