# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping, TokenBucket
from hc.test import BaseTestCase


class NotifyTelegramTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "DB Backup"
        self.check.tags = "foo bar baz"
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.n_pings = 1
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=10)
        self.ping.n = 112233
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "telegram"
        self.channel.value = json.dumps({"id": 123})
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

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["chat_id"], 123)
        self.assertIsNone(payload["message_thread_id"])
        self.assertIn("The check", payload["text"])
        self.assertIn(">DB Backup</a>", payload["text"])
        self.assertIn(self.check.cloaked_url(), payload["text"])

        self.assertIn("<b>Project:</b> Alices Project\n", payload["text"])
        self.assertIn("<b>Tags:</b> foo, bar, baz\n", payload["text"])
        self.assertIn("<b>Period:</b> 1 day\n", payload["text"])
        self.assertIn("<b>Total Pings:</b> 112233\n", payload["text"])
        self.assertIn("<b>Last Ping:</b> Success, 10 minutes ago", payload["text"])

        # Only one check in the project, so there should be no note about
        # other checks:
        self.assertNotIn("All the other checks are up.", payload["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_exitstatus(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn(
            "<b>Last Ping:</b> Exit status 123, 10 minutes ago", payload["text"]
        )

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_sends_to_thread(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.value = json.dumps({"id": 123, "thread_id": 456})
        self.channel.save()
        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["chat_id"], 123)
        self.assertEqual(payload["message_thread_id"], 456)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_cron_schedule(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.kind = "cron"
        self.check.schedule = "* * * * MON-FRI"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn(
            "<b>Schedule:</b> <code>* * * * MON-FRI</code>\n", payload["text"]
        )
        self.assertIn("<b>Time Zone:</b> Europe/Riga\n", payload["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_returns_error(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 400
        mock_post.return_value.content = b'{"description": "Hi"}'

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, 'Received status code 400 with a message: "Hi"')

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_non_json_error(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json = Mock(side_effect=ValueError)

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 400")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_group_supergroup_migration(self, mock_post: Mock) -> None:
        error_response = Mock(status_code=400)
        error_response.content = b"""{
            "description": "Hello",
            "parameters": {"migrate_to_chat_id": -234}
        }"""

        mock_post.side_effect = [error_response, Mock(status_code=200)]

        self.channel.notify(self.flip)
        self.assertEqual(mock_post.call_count, 2)

        # The chat id should have been updated
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.telegram.id, -234)

        # There should be no logged error
        n = Notification.objects.get()
        self.assertEqual(n.error, "")

    def test_it_obeys_rate_limit(self) -> None:
        TokenBucket.objects.create(value="tg-123", tokens=0)

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Rate limit exceeded")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_all_other_checks_up_note(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "up"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("All the other checks are up.", payload["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_lists_other_down_checks(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        other = Check(project=self.project)
        other.name = "Foobar"
        other.status = "down"
        other.last_ping = now() - td(minutes=61)
        other.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("The following checks are also down", payload["text"])
        self.assertIn("Foobar", payload["text"])
        self.assertIn("(last ping: an hour ago)", payload["text"])
        self.assertIn(other.cloaked_url(), payload["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_other_checks_with_no_last_ping(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        Check.objects.create(project=self.project, status="down")

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("(last ping: never)", payload["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_show_more_than_10_other_checks(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        for i in range(0, 11):
            other = Check(project=self.project)
            other.name = f"Foobar #{i}"
            other.status = "down"
            other.last_ping = now() - td(minutes=61)
            other.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Foobar", payload["text"])
        self.assertIn("11 other checks are also down.", payload["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_disables_channel_on_403_group_deleted(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 403
        mock_post.return_value.content = b"""{
            "description": "Forbidden: the group chat was deleted"
        }"""

        self.channel.notify(self.flip)
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.disabled)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_disables_channel_on_403_bot_blocked(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 403
        mock_post.return_value.content = b"""{
            "description": "Forbidden: bot was blocked by the user"
        }"""

        self.channel.notify(self.flip)
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.disabled)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_last_ping_body(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World"
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("<b>Last Ping Body:</b>\n", payload["text"])
        self.assertIn("Hello World", payload["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_truncated_last_ping_body(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World" * 100
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("[truncated]", payload["text"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_escapes_html(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"<b>bold</b>\nfoo & bar"
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;\n", payload["text"])
        self.assertIn("foo &amp; bar", payload["text"])
