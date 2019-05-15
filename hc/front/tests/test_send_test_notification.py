from django.core import mail
from hc.api.models import Channel
from hc.test import BaseTestCase


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
