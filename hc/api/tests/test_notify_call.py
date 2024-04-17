# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.core import mail
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification
from hc.test import BaseTestCase


@override_settings(TWILIO_ACCOUNT="test", TWILIO_AUTH="dummy", TWILIO_FROM="+123")
class NotifyCallTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "foo"
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "call"
        self.channel.value = json.dumps({"label": "foo", "value": "+1234567890"})
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_call(self, mock_post: Mock) -> None:
        self.profile.call_limit = 1
        self.profile.save()

        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["To"], "+1234567890")
        self.assertIn("""The check "foo" is down.""", payload["Twiml"])

        n = Notification.objects.get()
        callback_path = f"/api/v3/notifications/{n.code}/status"
        self.assertTrue(payload["StatusCallback"].endswith(callback_path))

    @override_settings(TWILIO_ACCOUNT=None)
    def test_it_requires_twilio_configuration(self) -> None:
        self.channel.notify(self.flip)
        n = Notification.objects.get()
        self.assertEqual(n.error, "Call notifications are not enabled")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_call_limit(self, mock_post: Mock) -> None:
        # At limit already:
        self.profile.call_limit = 50
        self.profile.last_call_date = now()
        self.profile.calls_sent = 50
        self.profile.save()

        self.channel.notify(self.flip)
        mock_post.assert_not_called()

        n = Notification.objects.get()
        self.assertTrue("Monthly phone call limit exceeded" in n.error)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertEqual(email.subject, "Monthly Phone Call Limit Reached")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_call_limit_reset(self, mock_post: Mock) -> None:
        # At limit, but also into a new month
        self.profile.call_limit = 50
        self.profile.calls_sent = 50
        self.profile.last_call_date = now() - td(days=100)
        self.profile.save()

        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        mock_post.assert_called_once()

    @override_settings(TWILIO_FROM="+000")
    @patch("hc.api.transports.logger.debug", autospec=True)
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_disables_channel_on_21211(self, mock_post: Mock, debug: Mock) -> None:
        self.profile.call_limit = 1
        self.profile.save()

        # Twilio's error 21211 is "Invalid 'To' Phone Number"
        mock_post.return_value.status_code = 400
        mock_post.return_value.content = b"""{"code": 21211}"""

        self.channel.notify(self.flip)

        # Make sure the HTTP request was made only once (no retries):
        self.channel.refresh_from_db()
        self.assertTrue(self.channel.disabled)

        n = Notification.objects.get()
        self.assertEqual(n.error, "Invalid phone number")

        # It should give up after the first try
        self.assertEqual(mock_post.call_count, 1)

        # It should not log this event
        self.assertFalse(debug.called)
