from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase

MOCK_GITHUB = Mock()
MOCK_GITHUB.get_installation_access_token.return_value = "test-token"


@patch("hc.api.transports.close_old_connections", Mock())
@patch("hc.api.transports.github", MOCK_GITHUB)
@override_settings(GITHUB_PRIVATE_KEY="test-private-key")
class NotifyGitHubTestCase(BaseTestCase):
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
        self.channel.kind = "github"
        self.channel.value = json.dumps(
            {"installation_id": 123, "repo": "alice/foo", "labels": ["foo", "bar"]}
        )
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"
        self.flip.reason = "timeout"

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "DB Backup is DOWN")
        self.assertEqual(payload["labels"], ["foo", "bar"])
        self.assertIn("[DB Backup]", payload["body"])
        self.assertIn(self.check.cloaked_url(), payload["body"])
        self.assertIn("grace time passed", payload["body"])

        self.assertIn("**Project:** Alices Project\n", payload["body"])
        self.assertIn("**Tags:** `foo` `bar` `baz` \n", payload["body"])

        self.assertIn("**Period:** 1 day\n", payload["body"])
        self.assertIn("**Total Pings:** 112233\n", payload["body"])
        self.assertIn("**Last Ping:** Success, 10 minutes ago", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_reason_failure(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.flip.reason = "fail"
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("received a failure signal", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_exitstatus(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.kind = "fail"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("**Last Ping:** Exit status 123, 10 minutes ago", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_cron_schedule(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.kind = "cron"
        self.check.schedule = "* * * * MON-FRI"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("**Schedule:** `* * * * MON-FRI`\n", payload["body"])
        self.assertIn("**Time Zone:** Europe/Riga\n", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_oncalendar_schedule(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.kind = "oncalendar"
        self.check.schedule = "Mon 2-29"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("**Schedule:** `Mon 2-29`\n", payload["body"])
        self.assertIn("**Time Zone:** Europe/Riga\n", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_returns_error(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 400

        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Received status code 400")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_access_token(self, mock_post: Mock) -> None:
        with patch("hc.api.transports.github") as mock:
            mock.get_installation_access_token.return_value = None
            self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "GitHub denied access to alice/foo")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_shows_last_ping_body(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"Hello World"
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("**Last Ping Body:**\n", payload["body"])
        self.assertIn("Hello World", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_checks_for_backticks_in_body(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.ping.body_raw = b"``` surprise"
        self.ping.save()

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("Last Ping Body", payload["body"])
        self.assertNotIn("```", payload["body"])

    @override_settings(GITHUB_PRIVATE_KEY=None)
    def test_it_requires_github_private_key(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "GitHub notifications are not enabled.")
