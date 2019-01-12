from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


class AddSlackTestCase(BaseTestCase):
    @override_settings(SLACK_CLIENT_ID=None)
    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_slack/")
        self.assertContains(r, "Integration Settings", status_code=200)

    @override_settings(SLACK_CLIENT_ID=None)
    def test_it_works(self):
        form = {"value": "http://example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/integrations/add_slack/", form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "slack")
        self.assertEqual(c.value, "http://example.org")
        self.assertEqual(c.project, self.project)

    @override_settings(SLACK_CLIENT_ID=None)
    def test_it_rejects_bad_url(self):
        form = {"value": "not an URL"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/integrations/add_slack/", form)
        self.assertContains(r, "Enter a valid URL")
