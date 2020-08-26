from hc.api.models import Channel
from hc.test import BaseTestCase


class AddZulipTestCase(BaseTestCase):
    def setUp(self):
        super(AddZulipTestCase, self).setUp()
        self.url = "/projects/%s/add_zulip/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "open-source group chat app")

    def test_it_works(self):
        form = {
            "bot_email": "foo@example.org",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "general",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "zulip")
        self.assertEqual(c.zulip_bot_email, "foo@example.org")
        self.assertEqual(c.zulip_api_key, "fake-key")
        self.assertEqual(c.zulip_type, "stream")
        self.assertEqual(c.zulip_to, "general")

    def test_it_rejects_bad_email(self):
        form = {
            "bot_email": "not@an@email",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "general",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Enter a valid email address.")

    def test_it_rejects_missing_api_key(self):
        form = {
            "bot_email": "foo@example.org",
            "api_key": "",
            "mtype": "stream",
            "to": "general",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "This field is required.")

    def test_it_rejects_bad_mtype(self):
        form = {
            "bot_email": "foo@example.org",
            "api_key": "fake-key",
            "mtype": "this-should-not-work",
            "to": "general",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

    def test_it_rejects_missing_stream_name(self):
        form = {
            "bot_email": "foo@example.org",
            "api_key": "fake-key",
            "mtype": "stream",
            "to": "",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "This field is required.")

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
