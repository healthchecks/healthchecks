from hc.api.models import Channel
from hc.test import BaseTestCase


class AddPdTestCase(BaseTestCase):
    url = "/integrations/add_email/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Get an email message")

    def test_it_creates_channel(self):
        form = {"value": "alice@example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "email")
        self.assertEqual(c.value, "alice@example.org")
        self.assertFalse(c.email_verified)

    def test_team_access_works(self):
        form = {"value": "bob@example.org"}

        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, form)

        ch = Channel.objects.get()
        # Added by bob, but should belong to alice (bob has team access)
        self.assertEqual(ch.user, self.alice)

    def test_it_rejects_bad_email(self):
        form = {"value": "not an email address"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Enter a valid email address.")

    def test_it_trims_whitespace(self):
        form = {"value": "   alice@example.org   "}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.value, "alice@example.org")
