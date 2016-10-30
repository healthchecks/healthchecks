from hc.api.models import Channel
from hc.test import BaseTestCase


class AddPdTestCase(BaseTestCase):
    url = "/integrations/add_pd/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "incident management system")

    def test_it_works(self):
        # Integration key is 32 characters long
        form = {"value": "12345678901234567890123456789012"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "pd")
        self.assertEqual(c.value, "123456")

    def test_it_trims_whitespace(self):
        form = {"value": "   123456   "}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.value, "123456")
