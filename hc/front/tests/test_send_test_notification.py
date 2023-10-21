from __future__ import annotations

import json
from unittest.mock import Mock, patch

from django.core import mail
from django.test.utils import override_settings

from hc.api.models import Channel, Notification
from hc.test import BaseTestCase


class SendTestNotificationTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.channel = Channel(kind="email", project=self.project)
        self.channel.email_verified = True
        self.channel.value = "alice@example.org"
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/test/"

    def test_it_sends_test_email(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "Test notification sent!")

        # An email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertNotIn("X-Bounce-ID", email.extra_headers)
        self.assertIn("List-Unsubscribe", email.extra_headers)

        # It should update self.channel.last_notify
        self.channel.refresh_from_db()
        self.assertIsNotNone(self.channel.last_notify)

        # It should create a notification
        n = Notification.objects.get()
        self.assertEqual(n.channel, self.channel)
        self.assertEqual(n.error, "")

    def test_it_allows_readonly_user(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {})
        self.assertRedirects(r, self.channels_url)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

    def test_it_clears_channel_last_error(self) -> None:
        self.channel.last_error = "Something went wrong"
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, {})

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "")

    def test_it_sets_channel_last_error(self) -> None:
        self.channel.email_verified = False
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)

        self.assertContains(r, "Could not send a test notification")
        self.assertContains(r, "Email not verified")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Email not verified")

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_webhooks_with_no_down_url(self, mock_get: Mock) -> None:
        mock_get.return_value.status_code = 200

        self.channel.kind = "webhook"
        self.channel.value = json.dumps(
            {
                "method_down": "GET",
                "url_down": "",
                "body_down": "",
                "headers_down": {},
                "method_up": "GET",
                "url_up": "http://example-url",
                "body_up": "",
                "headers_up": {},
            }
        )
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "Test notification sent!")

        args, kwargs = mock_get.call_args
        self.assertEqual(args, ("get", "http://example-url"))

    def test_it_handles_webhooks_with_no_urls(self) -> None:
        self.channel.kind = "webhook"
        self.channel.value = json.dumps(
            {
                "method_down": "GET",
                "url_down": "",
                "body_down": "",
                "headers_down": {},
                "method_up": "GET",
                "url_up": "",
                "body_up": "",
                "headers_up": {},
            }
        )
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "Could not send a test notification")

    def test_it_checks_channel_ownership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertEqual(r.status_code, 404)

    @override_settings(TWILIO_ACCOUNT="test", TWILIO_AUTH="dummy", TWILIO_FROM="+000")
    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_up_only_sms_channel(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.kind = "sms"
        self.channel.value = json.dumps({"value": "+123", "up": True, "down": False})
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "Test notification sent!")

        payload = mock_post.call_args.kwargs["data"]
        self.assertIn("is UP", payload["Body"])

    @patch("hc.api.transports.curl.request", autospec=True)
    def test_it_handles_webhook_with_json_variable(self, mock_post: Mock) -> None:
        mock_post.return_value.status_code = 200

        self.channel.kind = "webhook"
        self.channel.value = json.dumps(
            {
                "method_down": "POST",
                "url_down": "https://example.org",
                "body_down": "$JSON",
                "headers_down": {},
            }
        )
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, {})

        payload = mock_post.call_args.kwargs["data"]
        body = json.loads(payload)
        self.assertEqual(body["name"], "TEST")

    def test_it_handles_group_channel(self) -> None:
        channel_email = Channel(project=self.project)
        channel_email.kind = "email"
        channel_email.value = "alice@example.org"
        channel_email.email_verified = True
        channel_email.save()

        self.channel.kind = "group"
        self.channel.value = f"{channel_email.code}"
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, {})

        # An email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        # It should create two notifications
        self.assertEqual(Notification.objects.count(), 2)
