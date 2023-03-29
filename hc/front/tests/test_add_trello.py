from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(TRELLO_APP_KEY="foo")
class AddTrelloTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = "/projects/%s/add_trello/" % self.project.code

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Trello")

    def test_it_works(self):
        form = {
            "token": "0" * 64,
            "board_name": "My Board",
            "list_name": "My List",
            "list_id": "1" * 32,
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "trello")
        self.assertEqual(c.trello_token, "0" * 64)
        self.assertEqual(c.project, self.project)

    def test_it_handles_256_char_token(self):
        form = {
            "token": "0" * 256,
            "board_name": "My Board",
            "list_name": "My List",
            "list_id": "1" * 32,
        }

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.trello_token, "0" * 256)

    @override_settings(TRELLO_APP_KEY=None)
    def test_it_requires_trello_app_key(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self):
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_requires_board_name(self):
        self.client.login(username="alice@example.org", password="password")

        form = {
            "token": "0" * 64,
            "board_name": "",
            "list_name": "My List",
            "list_id": "1" * 32,
        }

        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 400)
