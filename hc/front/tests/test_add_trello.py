import json

from hc.api.models import Channel
from hc.test import BaseTestCase


class AddPagerTreeTestCase(BaseTestCase):
    url = "/integrations/add_trello/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Trello")

    def test_it_works(self):
        form = {"settings": json.dumps({
            "token": "fake-token",
            "board_name": "My Board",
            "list_name": "My List",
            "list_id": "fake-list-id"
        })}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.kind, "trello")
        self.assertEqual(c.trello_token, "fake-token")
        self.assertEqual(c.user, self.alice)
        self.assertEqual(c.project, self.project)
