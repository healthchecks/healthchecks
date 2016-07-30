from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(PUSHOVER_API_TOKEN="token", PUSHOVER_SUBSCRIPTION_URL="url")
class AddChannelTestCase(BaseTestCase):

    def test_it_adds_email(self):
        url = "/integrations/add/"
        form = {"kind": "email", "value": "alice@example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, form)

        self.assertRedirects(r, "/integrations/")
        assert Channel.objects.count() == 1

    def test_team_access_works(self):
        url = "/integrations/add/"
        form = {"kind": "email", "value": "bob@example.org"}

        self.client.login(username="bob@example.org", password="password")
        self.client.post(url, form)

        ch = Channel.objects.get()
        # Added by bob, but should belong to alice (bob has team access)
        self.assertEqual(ch.user, self.alice)

    def test_it_trims_whitespace(self):
        """ Leading and trailing whitespace should get trimmed. """

        url = "/integrations/add/"
        form = {"kind": "email", "value": "   alice@example.org   "}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(url, form)

        q = Channel.objects.filter(value="alice@example.org")
        self.assertEqual(q.count(), 1)

    def test_it_rejects_bad_kind(self):
        url = "/integrations/add/"
        form = {"kind": "dog", "value": "Lassie"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url, form)

        assert r.status_code == 400, r.status_code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        kinds = ("email", "webhook", "pd", "pushover", "hipchat", "victorops")
        for frag in kinds:
            url = "/integrations/add_%s/" % frag
            r = self.client.get(url)
            self.assertContains(r, "Integration Settings", status_code=200)
