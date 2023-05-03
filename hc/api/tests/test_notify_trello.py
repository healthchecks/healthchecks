from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


@override_settings(TRELLO_APP_KEY="fake-trello-app-key")
class NotifyTrelloTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "trello"
        self.channel.value = json.dumps(
            {
                "token": "fake-token",
                "board_name": "My Board",
                "list_name": "My List",
                "list_id": "fake-list-id",
            }
        )
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        params = mock_post.call_args.kwargs["params"]
        self.assertEqual(params["idList"], "fake-list-id")
        self.assertEqual(params["name"], "Down: Foo")
        self.assertIn("Full Details", params["desc"])
        self.assertEqual(params["key"], "fake-trello-app-key")
        self.assertEqual(params["token"], "fake-token")

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_escape_name(self, mock_post):
        mock_post.return_value.status_code = 200

        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.check)

        params = mock_post.call_args.kwargs["params"]
        self.assertEqual(params["name"], "Down: Foo & Bar")
