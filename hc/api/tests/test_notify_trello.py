from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


@override_settings(TRELLO_APP_KEY="fake-trello-app-key")
class NotifyTrelloTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=10)
        self.ping.n = 112233
        self.ping.save()

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

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        params = mock_post.call_args.kwargs["params"]
        self.assertEqual(params["idList"], "fake-list-id")
        self.assertEqual(params["name"], "Down: Foo")
        self.assertIn("Full Details", params["desc"])
        self.assertIn("**Last Ping:** 10 minutes ago", params["desc"])
        self.assertEqual(params["key"], "fake-trello-app-key")
        self.assertEqual(params["token"], "fake-token")

    @override_settings(TRELLO_APP_KEY=None)
    def test_it_requires_trello_app_key(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Trello notifications are not enabled.")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_schedule_and_tz(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.check.kind = "cron"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)

        params = mock_post.call_args.kwargs["params"]
        a = "\u034f*"
        self.assertIn(f"**Schedule:** `{a} {a} {a} {a} {a}`", params["desc"])
        self.assertIn("**Time Zone:** Europe/Riga", params["desc"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_escape_name(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.flip)

        params = mock_post.call_args.kwargs["params"]
        self.assertEqual(params["name"], "Down: Foo & Bar")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.ping.delete()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        params = mock_post.call_args.kwargs["params"]
        self.assertIn("**Last Ping:** never", params["desc"])
