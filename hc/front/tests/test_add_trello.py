import json

from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


class AddTrelloTestCase(BaseTestCase):
    def setUp(self):
        super(AddTrelloTestCase, self).setUp()
        self.url = "/projects/%s/add_trello/" % self.project.code

    @override_settings(TRELLO_APP_KEY="foo")
    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Trello")

    @override_settings(TRELLO_APP_KEY="foo")
    def test_it_works(self):
        form = {
            "settings": json.dumps(
                {
                    "token": "fake-token",
                    "board_name": "My Board",
                    "list_name": "My List",
                    "list_id": "fake-list-id",
                }
            )
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "trello")
        self.assertEqual(c.trello_token, "fake-token")
        self.assertEqual(c.project, self.project)
