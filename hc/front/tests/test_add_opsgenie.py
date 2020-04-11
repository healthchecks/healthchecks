import json

from hc.api.models import Channel
from hc.test import BaseTestCase


class AddOpsGenieTestCase(BaseTestCase):
    def setUp(self):
        super(AddOpsGenieTestCase, self).setUp()
        self.url = "/projects/%s/add_opsgenie/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "escalation policies and incident tracking")

    def test_it_works(self):
        form = {"key": "123456", "region": "us"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "opsgenie")

        payload = json.loads(c.value)
        self.assertEqual(payload["key"], "123456")
        self.assertEqual(payload["region"], "us")
        self.assertEqual(c.project, self.project)

    def test_it_trims_whitespace(self):
        form = {"key": "   123456   ", "region": "us"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        payload = json.loads(c.value)
        self.assertEqual(payload["key"], "123456")

    def test_it_saves_eu_region(self):
        form = {"key": "123456", "region": "eu"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        payload = json.loads(c.value)
        self.assertEqual(payload["region"], "eu")
