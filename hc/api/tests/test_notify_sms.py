# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.core import mail
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


@override_settings(TWILIO_ACCOUNT="test", TWILIO_AUTH="dummy")
class NotifySmsTestCase(BaseTestCase):
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

        spec = {"value": "+1234567890", "up": False, "down": True}
        self.channel = Channel(project=self.project, kind="sms")
        self.channel.value = json.dumps(spec)
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"

    @override_settings(TWILIO_FROM="+000", TWILIO_MESSAGING_SERVICE_SID=None)
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_works(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["To"], "+1234567890")
        self.assertEqual(payload["From"], "+000")
        self.assertNotIn("\xa0", payload["Body"])
        self.assertIn("""The check "Foo" is DOWN.""", payload["Body"])
        self.assertIn("""Last ping was 10 minutes ago.""", payload["Body"])

        n = Notification.objects.get()
        callback_path = f"/api/v3/notifications/{n.code}/status"
        self.assertTrue(payload["StatusCallback"].endswith(callback_path))

        # sent SMS counter should go up
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sms_sent, 1)

    @override_settings(TWILIO_ACCOUNT=None)
    def test_it_requires_twilio_configuration(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "SMS notifications are not enabled")

    @override_settings(TWILIO_MESSAGING_SERVICE_SID="dummy-sid")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_uses_messaging_service(self, mock_post: Mock) -> None:
        self.check.last_ping = now() - td(hours=2)
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["MessagingServiceSid"], "dummy-sid")
        self.assertFalse("From" in payload)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_enforces_limit(self, mock_post: Mock) -> None:
        # At limit already:
        self.profile.last_sms_date = now()
        self.profile.sms_sent = 50
        self.profile.save()

        self.channel.notify(self.flip)
        mock_post.assert_not_called()

        n = Notification.objects.get()
        self.assertTrue("Monthly SMS limit exceeded" in n.error)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertEqual(email.subject, "Monthly SMS Limit Reached")

    @override_settings(TWILIO_FROM="+000")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_resets_limit_next_month(self, mock_post: Mock) -> None:
        # At limit, but also into a new month
        self.profile.sms_sent = 50
        self.profile.last_sms_date = now() - td(days=100)
        self.profile.save()

        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)
        mock_post.assert_called_once()

    @override_settings(TWILIO_FROM="+000")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_escape_special_characters(self, mock_post: Mock) -> None:
        self.check.name = "Foo > Bar & Co"
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertIn("Foo > Bar & Co", payload["Body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_disabled_down_notification(self, mock_post: Mock) -> None:
        payload = {"value": "+123123123", "up": True, "down": False}
        self.channel.value = json.dumps(payload)

        self.channel.notify(self.flip)
        mock_post.assert_not_called()

    @override_settings(TWILIO_FROM="+000")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_sends_up_notification(self, mock_post: Mock) -> None:
        payload = {"value": "+123123123", "up": True, "down": False}
        self.channel.value = json.dumps(payload)

        self.flip.old_status = "down"
        self.flip.new_status = "up"
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        assert isinstance(payload["Body"], str)
        self.assertIn("is UP", payload["Body"])

    @override_settings(TWILIO_FROM="+000")
    @patch("hc.api.transports.logger.debug", autospec=True)
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_disables_channel_on_21211(self, mock_post: Mock, debug: Mock) -> None:
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

    @override_settings(TWILIO_FROM="+000", TWILIO_MESSAGING_SERVICE_SID=None)
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_no_last_ping(self, mock_post: Mock) -> None:
        self.ping.delete()
        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertNotIn("""Last ping was""", payload["Body"])
