from hc.api.models import Channel
from hc.test import BaseTestCase


class AddSlackTestCase(BaseTestCase):
    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_apprise/")
        self.assertContains(r, "Integration Settings", status_code=200)

    def test_it_works(self):
        form = {"url": "json://example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/integrations/add_apprise/", form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "apprise")
        self.assertEqual(c.value, "json://example.org")
        self.assertEqual(c.project, self.project)
