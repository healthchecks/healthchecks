from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


class AddMattermostTestCase(BaseTestCase):
    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_mattermost/")
        self.assertContains(r, "Integration Settings", status_code=200)

    def test_it_works(self):
        form = {"value": "http://example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/integrations/add_mattermost/", form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "mattermost")
        self.assertEqual(c.value, "http://example.org")
        self.assertEqual(c.project, self.project)
