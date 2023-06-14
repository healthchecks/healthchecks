# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.core import mail
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyWhatsAppTestCase(BaseTestCase):
    def _setup_data(self, notify_up=True, notify_down=True):
        self.check = Check(project=self.project)
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        definition = {"value": "+1234567890", "up": notify_up, "down": notify_down}

        self.channel = Channel(project=self.project, kind="whatsapp")
        self.channel.value = json.dumps(definition)
        self.channel.save()
        self.channel.checks.add(self.check)

    @override_settings(TWILIO_FROM="+000", TWILIO_MESSAGING_SERVICE_SID=None)
    @patch("hc.api.transports.curl.request")
    def test_it_works(self, mock_post):
        mock_post.return_value.status_code = 200
        self._setup_data()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["From"], "whatsapp:+000")
        self.assertEqual(payload["To"], "whatsapp:+1234567890")

        n = Notification.objects.get()
        callback_path = f"/api/v3/notifications/{n.code}/status"
        self.assertTrue(payload["StatusCallback"].endswith(callback_path))

        # sent SMS counter should go up
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sms_sent, 1)

    @override_settings(TWILIO_MESSAGING_SERVICE_SID="dummy-sid")
    @patch("hc.api.transports.curl.request")
    def test_it_uses_messaging_service(self, mock_post):
        mock_post.return_value.status_code = 200
        self._setup_data()

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertEqual(payload["MessagingServiceSid"], "dummy-sid")
        self.assertFalse("From" in payload)

    @patch("hc.api.transports.curl.request")
    def test_it_obeys_up_down_flags(self, mock_post):
        self._setup_data(notify_down=False)
        self.check.last_ping = now() - td(hours=2)

        self.channel.notify(self.check)
        self.assertEqual(Notification.objects.count(), 0)
        mock_post.assert_not_called()

    @patch("hc.api.transports.curl.request")
    def test_it_enforces_limit(self, mock_post):
        # At limit already:
        self.profile.last_sms_date = now()
        self.profile.sms_sent = 50
        self.profile.save()

        self._setup_data()

        self.channel.notify(self.check)
        mock_post.assert_not_called()

        n = Notification.objects.get()
        self.assertTrue("Monthly message limit exceeded" in n.error)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertEqual(email.subject, "Monthly WhatsApp Limit Reached")

    @patch("hc.api.transports.curl.request")
    def test_it_does_not_escape_special_characters(self, mock_post):
        self._setup_data()
        self.check.name = "Foo > Bar & Co"

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)

        payload = mock_post.call_args.kwargs["data"]
        self.assertIn("Foo > Bar & Co", payload["Body"])
