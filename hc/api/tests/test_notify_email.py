# coding: utf-8

from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test.utils import override_settings
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
        self.ping.n = 1
        self.ping.remote_addr = "1.2.3.4"
        self.ping.body_raw = b"Body Line 1\nBody Line 2"
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "email"
        self.channel.value = "alice@example.org"
        self.channel.email_verified = True
        self.channel.save()
        self.channel.checks.add(self.check)

    @override_settings(DEFAULT_FROM_EMAIL="alerts@example.org")
    def test_it_works(self):
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertNotIn("X-Bounce-ID", email.extra_headers)
        self.assertTrue("List-Unsubscribe" in email.extra_headers)
        self.assertTrue("List-Unsubscribe-Post" in email.extra_headers)
        self.assertTrue(email.extra_headers["Message-ID"].endswith("@example.org>"))

        html = email.alternatives[0][0]
        # Name
        self.assertIn("Daily Backup", email.body)
        self.assertIn("Daily Backup", html)

        # Description
        self.assertIn("Line 1\nLine2", email.body)
        self.assertIn("Line 1<br>Line2", html)

        # Project
        self.assertIn("Alices Project", email.body)
        self.assertIn("Alices Project", html)

        # Tags
        self.assertIn("foo bar", email.body)
        self.assertIn("foo</code>", html)
        self.assertIn("bar</code>", html)

        # Period
        self.assertIn("1 day", email.body)
        self.assertIn("1 day", html)

        # Source IP
        self.assertIn("from 1.2.3.4", email.body)
        self.assertIn("from 1.2.3.4", html)

        # Total pings
        self.assertIn("112233", email.body)
        self.assertIn("112233", html)

        # Last ping body
        self.assertIn("Body Line 1\nBody Line 2", email.body)
        self.assertIn("Body Line 1<br>Body Line 2", html)

        # Check's code must not be in the html
        self.assertNotIn(str(self.check.code), html)

        # Check's code must not be in the plain text body
        self.assertNotIn(str(self.check.code), email.body)

    @override_settings(DEFAULT_FROM_EMAIL='"Alerts" <alerts@example.org>')
    def test_it_message_id_generation_handles_angle_brackets(self):
        self.channel.notify(self.check)

        email = mail.outbox[0]
        self.assertTrue(email.extra_headers["Message-ID"].endswith("@example.org>"))

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.get_object")
    def test_it_loads_body_from_object_storage(self, get_object):
        get_object.return_value = b"Body Line 1\nBody Line 2"

        self.ping.object_size = 1000
        self.ping.body_raw = None
        self.ping.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]
        self.assertIn("Line 1<br>Line2", html)

        code, n = get_object.call_args.args
        self.assertEqual(code, self.check.code)
        self.assertEqual(n, 1)

    def test_it_shows_cron_schedule(self):
        self.check.kind = "cron"
        self.check.schedule = "0 18-23,0-8 * * *"
        self.check.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]

        self.assertIn("0 18-23,0-8 * * *", email.body)
        self.assertIn("<code>0 18-23,0-8 * * *</code>", html)

    def test_it_truncates_long_body(self):
        self.ping.body = "X" * 10000 + ", and the rest gets cut off"
        self.ping.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]

        self.assertIn("[truncated]", email.body)
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

        self.assertNotIn("Projects Overview", email.body)
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

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.get_object")
    def test_it_handles_pending_body(self, get_object):
        get_object.return_value = None

        self.ping.object_size = 1000
        self.ping.body_raw = None
        self.ping.save()

        with patch("hc.api.transports.time.sleep"):
            self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]

        self.assertIn("The request body data is being processed", email.body)
        self.assertIn("The request body data is being processed", html)

    def test_it_shows_ignored_nonzero_exitstatus(self):
        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]
        self.assertIn("Ignored", email.body)
        self.assertIn("Ignored", html)

    def test_it_handles_last_ping_log(self):
        self.ping.kind = "log"
        self.ping.save()

        self.channel.notify(self.check)

        email = mail.outbox[0]
        html = email.alternatives[0][0]
        self.assertIn("Log", email.body)
        self.assertIn("Log", html)

    @override_settings(EMAIL_MAIL_FROM_TMPL="%s@bounces.example.org")
    def test_it_sets_custom_mail_from(self):
        self.channel.notify(self.check)

        email = mail.outbox[0]
        self.assertTrue(email.from_email.startswith("n."))
        self.assertTrue(email.from_email.endswith("@bounces.example.org"))
        # The From header should contain the display address
        self.assertEqual(email.extra_headers["From"], settings.DEFAULT_FROM_EMAIL)
        # There should be no X-Bounce-ID header
        self.assertNotIn("X-Bounce-ID", email.extra_headers)
