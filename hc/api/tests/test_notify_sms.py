# coding: utf-8

from datetime import timedelta as td
import json
from unittest.mock import patch

from django.core import mail
from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase


class NotifyTestCase(BaseTestCase):
    def _setup_data(self, value):
        self.check = Check(project=self.project)
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project, kind="sms")
        self.channel.value = value
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.requests.request")
    def test_it_works(self, mock_post):
        self._setup_data("+1234567890")
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertEqual(payload["To"], "+1234567890")
        self.assertFalse("\xa0" in payload["Body"])

        n = Notification.objects.get()
        callback_path = f"/api/v1/notifications/{n.code}/status"
        self.assertTrue(payload["StatusCallback"].endswith(callback_path))

        # sent SMS counter should go up
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.sms_sent, 1)

    @patch("hc.api.transports.requests.request")
    def test_it_handles_json_value(self, mock_post):
        value = {"label": "foo", "value": "+1234567890"}
        self._setup_data(json.dumps(value))
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertEqual(payload["To"], "+1234567890")

    @patch("hc.api.transports.requests.request")
    def test_it_enforces_limit(self, mock_post):
        # At limit already:
        self.profile.last_sms_date = now()
        self.profile.sms_sent = 50
        self.profile.save()

        self._setup_data("+1234567890")

        self.channel.notify(self.check)
        self.assertFalse(mock_post.called)

        n = Notification.objects.get()
        self.assertTrue("Monthly SMS limit exceeded" in n.error)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertEqual(email.subject, "Monthly SMS Limit Reached")

    @patch("hc.api.transports.requests.request")
    def test_it_resets_limit_next_month(self, mock_post):
        # At limit, but also into a new month
        self.profile.sms_sent = 50
        self.profile.last_sms_date = now() - td(days=100)
        self.profile.save()

        self._setup_data("+1234567890")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        self.assertTrue(mock_post.called)

    @patch("hc.api.transports.requests.request")
    def test_it_does_not_escape_special_characters(self, mock_post):
        self._setup_data("+1234567890")
        self.check.name = "Foo > Bar & Co"
        self.check.last_ping = now() - td(hours=2)

        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)

        args, kwargs = mock_post.call_args
        payload = kwargs["data"]
        self.assertIn("Foo > Bar & Co", payload["Body"])
