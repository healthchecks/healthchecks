# coding: utf-8

from datetime import timedelta as td
import json

from django.core import mail
from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification, Ping
from hc.test import BaseTestCase


class NotifyEmailTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Daily Backup"
        self.check.desc = "Line 1\nLine2"
        self.check.tags = "foo bar"
        self.check.status = "down"
        self.check.last_ping = now() - td(minutes=61)
        self.check.n_pings = 112233
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.remote_addr = "1.2.3.4"
        self.ping.body = "Body Line 1\nBody Line 2"
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "email"
        self.channel.value = "alice@example.org"
        self.channel.email_verified = True
        self.channel.save()
        self.channel.checks.add(self.check)

    def test_email(self):
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertTrue("X-Status-Url" in email.extra_headers)
        self.assertTrue("List-Unsubscribe" in email.extra_headers)
        self.assertTrue("List-Unsubscribe-Post" in email.extra_headers)

        html = email.alternatives[0][0]
        self.assertIn("Daily Backup", html)
        self.assertIn("Line 1<br>Line2", html)
        self.assertIn("Alices Project", html)
        self.assertIn("foo</code>", html)
        self.assertIn("bar</code>", html)
        self.assertIn("1 day", html)
        self.assertIn("from 1.2.3.4", html)
        self.assertIn("112233", html)
        self.assertIn("Body Line 1<br>Body Line 2", html)

    def test_it_shows_cron_schedule(self):
        self.check.kind = "cron"
        self.check.schedule = "0 18-23,0-8 * * *"
        self.check.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]

        self.assertIn("<code>0 18-23,0-8 * * *</code>", html)

    def test_it_truncates_long_body(self):
        self.ping.body = "X" * 10000 + ", and the rest gets cut off"
        self.ping.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]

        self.assertIn("[truncated]", html)
        self.assertNotIn("the rest gets cut off", html)

    def test_it_handles_missing_ping_object(self):
        self.ping.delete()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]

        self.assertIn("Daily Backup", html)

    def test_it_handles_missing_profile(self):
        self.channel.value = "alice+notifications@example.org"
        self.channel.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice+notifications@example.org")

        html = email.alternatives[0][0]
        self.assertIn("Daily Backup", html)
        self.assertNotIn("Projects Overview", html)

    def test_email_transport_handles_json_value(self):
        payload = {"value": "alice@example.org", "up": True, "down": True}
        self.channel.value = json.dumps(payload)
        self.channel.save()

        self.channel.notify(self.check)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")

    def test_it_reports_unverified_email(self):
        self.channel.email_verified = False
        self.channel.save()

        self.channel.notify(self.check)

        # If an email is not verified, it should say so in the notification:
        n = Notification.objects.get()
        self.assertEqual(n.error, "Email not verified")

    def test_email_checks_up_down_flags(self):
        payload = {"value": "alice@example.org", "up": True, "down": False}
        self.channel.value = json.dumps(payload)
        self.channel.save()

        self.channel.notify(self.check)

        # This channel should not notify on "down" events:
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_handles_amperstand(self):
        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "DOWN | Foo & Bar")
