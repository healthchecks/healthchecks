from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyPushbulletTestCase(BaseTestCase):
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
        self.channel.kind = "pushbullet"
        self.channel.value = "fake-token"
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "up"
        self.flip.new_status = "down"
        self.flip.reason = "timeout"

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Access-Token"], "fake-token")
        payload = kwargs["json"]
        self.assertEqual(payload["type"], "note")
        self.assertIn("""The check "Foo" is DOWN""", payload["body"])
        self.assertIn("grace time passed", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_reason_fail(self, mock_post: Mock) -> None:
        self.flip.reason = "fail"
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertIn("received a failure signal", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_reports_down_duration(self, mock_post: Mock) -> None:
        self.flip.save()

        up_flip = Flip(owner=self.check)
        up_flip.created = self.flip.created + td(minutes=90)
        up_flip.old_status = "down"
        up_flip.new_status = "up"
        self.channel.notify(up_flip)

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertIn("The downtime lasted 1 hour, 30 minutes.", payload["body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_up(self, mock_post: Mock) -> None:
        self.flip.old_status = "down"
        self.flip.new_status = "up"
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        assert Notification.objects.count() == 1

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["type"], "note")
        self.assertEqual(kwargs["json"]["body"], 'The check "Foo" is UP.')
        self.assertEqual(kwargs["headers"]["Access-Token"], "fake-token")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_escapes_body(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200
        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.flip)

        _, kwargs = mock_post.call_args
        self.assertIn(
            'The check "Foo & Bar" is DOWN ',
            kwargs["json"]["body"],
        )
