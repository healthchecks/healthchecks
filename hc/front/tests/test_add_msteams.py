from hc.api.models import Channel
from hc.test import BaseTestCase


class AddMsTeamsTestCase(BaseTestCase):
    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/integrations/add_msteams/")
        self.assertContains(r, "Integration Settings", status_code=200)

    def test_it_works(self):
        form = {"value": "https://example.com/foo"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/integrations/add_msteams/", form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "msteams")
        self.assertEqual(c.value, "https://example.com/foo")
        self.assertEqual(c.project, self.project)
