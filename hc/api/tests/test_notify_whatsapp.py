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


@override_settings(
    TWILIO_USE_WHATSAPP=True,
    TWILIO_ACCOUNT="test",
    TWILIO_AUTH="dummy",
    TWILIO_MESSAGING_SERVICE_SID="MGx",
    TWILIO_FROM="+000",
    WHATSAPP_UP_CONTENT_SID="HXup",
    WHATSAPP_DOWN_CONTENT_SID="HXdown",
)
class NotifyWhatsAppTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Foo"
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.save()

        definition = {"value": "+1234567890", "up": True, "down": True}

        self.channel = Channel(project=self.project, kind="whatsapp")
        self.channel.value = json.dumps(definition)
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

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["From"], "whatsapp:+000")
        self.assertEqual(payload["To"], "whatsapp:+1234567890")
        self.assertEqual(payload["MessagingServiceSid"], "MGx")
        self.assertEqual(payload["ContentSid"], "HXdown")

        variables = json.loads(payload["ContentVariables"])
        self.assertEqual(variables["1"], "Foo")

        n = Notification.objects.get()
        callback_path = f"/api/v3/notifications/{n.code}/status"
        self.assertTrue(payload["StatusCallback"].endswith(callback_path))

        # sent SMS counter should go up
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sms_sent, 1)

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_last_ping_now(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.check.last_ping = now()
        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        variables = json.loads(payload["ContentVariables"])
        self.assertEqual(variables["1"], "Foo")

    @override_settings(TWILIO_ACCOUNT=None)
    def test_it_requires_twilio_account(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "WhatsApp notifications are not enabled")

    @override_settings(WHATSAPP_UP_CONTENT_SID=None)
    def test_it_requires_content_template_sids(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "WhatsApp notifications are not enabled")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_obeys_up_down_flags(self, mock_post: Mock) -> None:
        definition = {"value": "+1234567890", "up": True, "down": False}
        self.channel.value = json.dumps(definition)
        self.channel.save()

        self.check.last_ping = now() - td(hours=2)

        self.channel.notify(self.flip)
        self.assertEqual(Notification.objects.count(), 0)
        mock_post.assert_not_called()

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_enforces_limit(self, mock_post: Mock) -> None:
        # At limit already:
        self.profile.last_sms_date = now()
        self.profile.sms_sent = 50
        self.profile.save()

        self.channel.notify(self.flip)
        mock_post.assert_not_called()

        n = Notification.objects.get()
        self.assertTrue("Monthly message limit exceeded" in n.error)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertEqual(email.subject, "Monthly WhatsApp Limit Reached")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_does_not_escape_special_characters(self, mock_post: Mock) -> None:
        self.check.name = "Foo > Bar & Co"

        mock_post.return_value.status_code = 200

        self.channel.notify(self.flip)

        payload = mock_post.call_args.kwargs["data"]
        self.assertIn("Foo > Bar & Co", payload["ContentVariables"])

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
