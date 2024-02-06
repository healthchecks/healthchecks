from __future__ import annotations

import json
from unittest.mock import Mock, patch

from django.test.utils import override_settings

from hc.test import BaseTestCase


@override_settings(TRELLO_APP_KEY="foo")
class AddTrelloTestCase(BaseTestCase):
    url = "/integrations/add_trello/settings/"

    @patch("hc.front.views.curl.get", autospec=True)
    def test_it_works(self, mock_get: Mock) -> None:
        mock_get.return_value.content = json.dumps(
            [{"id": "1", "name": "My Board", "lists": [{"id": "2", "name": "Alerts"}]}]
        )

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertContains(r, "Please select the Trello list")
        self.assertContains(r, "Alerts")

    @override_settings(TRELLO_APP_KEY=None)
    def test_it_requires_trello_app_key(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    @patch("hc.front.views.curl.get", autospec=True)
    def test_it_handles_no_lists(self, mock_get: Mock) -> None:
        mock_get.return_value.content = "[]"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertNotContains(r, "Please select the Trello list")
        self.assertContains(r, "Could not find any boards with lists")

    @patch("hc.front.views.curl.get", autospec=True)
    def test_it_handles_unexpected_response_from_trello(self, mock_get: Mock) -> None:
        for sample in ("surprise", "{}", """{"lists": "surprise"}"""):
            mock_get.return_value.content = sample

            self.client.login(username="alice@example.org", password="password")

            with patch("hc.front.views.logger") as logger:
                r = self.client.post(self.url)
                self.assertContains(r, "Received an unexpected response from Trello")
                self.assertTrue(logger.warning.called)
