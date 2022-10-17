# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification, TokenBucket
from hc.test import BaseTestCase


class NotifyTelegramTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "telegram"
        self.channel.value = json.dumps({"id": 123})
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["chat_id"], 123)
        self.assertIn("The check", payload["text"])
        self.assertIn(self.check.cloaked_url(), payload["text"])

        # Only one check in the project, so there should be no note about
        # other checks:
        self.assertNotIn("All the other checks are up.", payload["text"])

    @patch("hc.api.transports.curl.request")
    def test_it_returns_error(self, mock_post):
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"description": "Hi"}

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, 'Received status code 400 with a message: "Hi"')

    @patch("hc.api.transports.curl.request")
    def test_it_handles_non_json_error(self, mock_post):
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = Mock(side_effect=ValueError)

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 400")

    @patch("hc.api.transports.curl.request")
    def test_it_handles_group_supergroup_migration(self, mock_post):
        error_response = Mock(status_code=400)
        error_response.json.return_value = {
            "description": "Hello",
            "parameters": {"migrate_to_chat_id": -234},
        }

        mock_post.side_effect = [error_response, Mock(status_code=200)]

        self.channel.notify(self.check)
        self.assertEqual(mock_post.call_count, 2)

        # The chat id should have been updated
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.telegram_id, -234)

        # There should be no logged error
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

    def test_telegram_obeys_rate_limit(self):
        TokenBucket.objects.create(value="tg-123", tokens=0)

        self.channel.notify(self.check)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Rate limit exceeded")

    @patch("hc.api.transports.curl.request")
    def test_it_shows_all_other_checks_up_note(self, mock_post):
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "up"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertIn("All the other checks are up.", payload["text"])

    @patch("hc.api.transports.curl.request")
    def test_it_lists_other_down_checks(self, mock_post):
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "down"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.check)

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertIn("The following checks are also down", payload["text"])
        self.assertIn("Foobar", payload["text"])
        self.assertIn(other.cloaked_url(), payload["text"])

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_show_more_than_10_other_checks(self, mock_post):
        mock_post.return_value.status_code = 200

        for i in range(0, 11):
            other = Check(project=self.project)
            other.name = f"Foobar #{i}"
            other.status = "down"
            other.last_ping = now() - td(minutes=61)
            other.save()

        self.channel.notify(self.check)

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertNotIn("Foobar", payload["text"])
        self.assertIn("11 other checks are also down.", payload["text"])

    @patch("hc.api.transports.curl.request")
    def test_it_disables_channel_on_403_group_deleted(self, mock_post):
        mock_post.return_value.status_code = 403
        mock_post.return_value.json.return_value = {
            "description": "Forbidden: the group chat was deleted"
        }

        self.channel.notify(self.check)
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.disabled)
