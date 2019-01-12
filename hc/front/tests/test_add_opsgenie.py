from hc.api.models import Channel
from hc.test import BaseTestCase


class AddOpsGenieTestCase(BaseTestCase):
    url = "/integrations/add_opsgenie/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "escalation policies and incident tracking")

    def test_it_works(self):
        form = {"value": "123456"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "opsgenie")
        self.assertEqual(c.value, "123456")
        self.assertEqual(c.project, self.project)

    def test_it_trims_whitespace(self):
        form = {"value": "   123456   "}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.value, "123456")
