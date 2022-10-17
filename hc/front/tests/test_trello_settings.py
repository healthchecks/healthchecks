from __future__ import annotations

from unittest.mock import patch

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(TRELLO_APP_KEY="foo")
class AddTrelloTestCase(BaseTestCase):
    url = "/integrations/add_trello/settings/"

    @patch("hc.front.views.curl.get")
    def test_it_works(self, mock_get):
        mock_get.return_value.json.return_value = [
            {"name": "My Board", "lists": [{"name": "Alerts"}]}
        ]

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertContains(r, "Please select the Trello list")
        self.assertContains(r, "Alerts")

    @override_settings(TRELLO_APP_KEY=None)
    def test_it_requires_trello_app_key(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    @patch("hc.front.views.curl.get")
    def test_it_handles_no_lists(self, mock_get):
        mock_get.return_value.json.return_value = []

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertNotContains(r, "Please select the Trello list")
        self.assertContains(r, "Could not find any boards with lists")
