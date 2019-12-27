import json

from django.core import mail
from hc.api.models import Channel
from hc.test import BaseTestCase
from mock import patch


class SendTestNotificationTestCase(BaseTestCase):
    def setUp(self):
        super(SendTestNotificationTestCase, self).setUp()
        self.channel = Channel(kind="email", project=self.project)
        self.channel.email_verified = True
        self.channel.value = "alice@example.org"
        self.channel.save()

        self.url = "/integrations/%s/test/" % self.channel.code

    def test_it_sends_test_email(self):

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(r, "/integrations/")
        self.assertContains(r, "Test notification sent!")

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertTrue("X-Bounce-Url" in email.extra_headers)
        self.assertTrue("List-Unsubscribe" in email.extra_headers)

    @patch("hc.api.transports.requests.request")
    def test_it_handles_webhooks_with_no_down_url(self, mock_get):
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
        self.assertRedirects(r, "/integrations/")
        self.assertContains(r, "Test notification sent!")

    def test_it_handles_webhooks_with_no_urls(self):
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
        self.assertRedirects(r, "/integrations/")
        self.assertContains(r, "Could not send a test notification")
