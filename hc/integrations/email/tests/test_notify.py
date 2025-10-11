from __future__ import annotations

import json
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.conf import settings
from django.core import mail
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Flip, Notification, Ping
from hc.test import BaseTestCase


class NotifyEmailTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project)
        self.check.name = "Daily Backup"
        self.check.desc = "Line 1\nLine2"
        self.check.tags = "foo bar"
        # Transport classes should use flip.new_status,
        # so the status "paused" should not appear anywhere
        self.check.status = "paused"
        self.check.last_ping = now()
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.created = now() - td(minutes=61)
        self.ping.n = 112233
        self.ping.remote_addr = "1.2.3.4"
        self.ping.body_raw = b"Body Line 1\nBody Line 2"
        self.ping.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "email"
        self.channel.value = "alice@example.org"
        self.channel.email_verified = True
        self.channel.save()
        self.channel.checks.add(self.check)

        self.flip = Flip(owner=self.check)
        self.flip.created = now()
        self.flip.old_status = "new"
        self.flip.new_status = "down"
        self.flip.reason = "timeout"

    @override_settings(DEFAULT_FROM_EMAIL="alerts@example.org")
    def test_it_works(self) -> None:
        self.channel.notify(self.flip)

        n = Notification.objects.get()
        self.assertEqual(n.error, "")

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "DOWN | Daily Backup")
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertNotIn("X-Bounce-ID", email.extra_headers)
        self.assertTrue("List-Unsubscribe" in email.extra_headers)
        self.assertTrue("List-Unsubscribe-Post" in email.extra_headers)
        self.assertTrue(email.extra_headers["Message-ID"].endswith("@example.org>"))

        # Message
        self.assertEmailContainsText("""The check "Daily Backup" has gone down.""")
        self.assertEmailContainsHtml(""""Daily Backup" is DOWN""")
        self.assertEmailContains("grace time passed")

        # Description
        self.assertEmailContainsText("Line 1\nLine2")
        self.assertEmailContainsHtml("Line 1<br>Line2")

        # Project
        self.assertEmailContains("Alices Project")

        # Tags
        self.assertEmailContainsText("foo bar")
        self.assertEmailContainsHtml("foo</code>")
        self.assertEmailContainsHtml("bar</code>")

        # Period
        self.assertEmailContains("1 day")

        # Source IP
        self.assertEmailContains("from 1.2.3.4")

        # Total pings
        self.assertEmailContains("112233")

        # Last ping time
        self.assertEmailContains("an hour ago")

        # Last ping body
        self.assertEmailContainsText("Body Line 1\nBody Line 2")
        self.assertEmailContainsHtml("Body Line 1<br>Body Line 2")

        # Check's code must not be in the plain text or html
        self.assertEmailNotContains(str(self.check.code))

    @override_settings(DEFAULT_FROM_EMAIL="alerts@example.org")
    def test_it_handles_reason_failure(self) -> None:
        self.flip.reason = "fail"
        self.channel.notify(self.flip)

        self.assertEmailContains("received a failure signal")

    @override_settings(DEFAULT_FROM_EMAIL='"Alerts" <alerts@example.org>')
    def test_it_message_id_generation_handles_angle_brackets(self) -> None:
        self.channel.notify(self.flip)

        email = mail.outbox[0]
        self.assertTrue(email.extra_headers["Message-ID"].endswith("@example.org>"))

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.get_object")
    def test_it_loads_body_from_object_storage(self, get_object: Mock) -> None:
        get_object.return_value = b"Body Line 1\nBody Line 2"

        self.ping.object_size = 1000
        self.ping.body_raw = None
        self.ping.save()

        self.channel.notify(self.flip)
        self.assertEmailContainsHtml("Line 1<br>Line2")

        code, n = get_object.call_args.args
        self.assertEqual(code, str(self.check.code))
        self.assertEqual(n, 112233)

    def test_it_shows_cron_schedule(self) -> None:
        self.check.kind = "cron"
        self.check.schedule = "0 18-23,0-8 * * *"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)

        self.assertEmailContainsText("0 18-23,0-8 * * *")
        self.assertEmailContainsHtml("<code>0 18-23,0-8 * * *</code>")
        self.assertEmailContains("Europe/Riga")

    def test_it_shows_oncalendar_schedule(self) -> None:
        self.check.kind = "oncalendar"
        self.check.schedule = "Mon 2-29"
        self.check.tz = "Europe/Riga"
        self.check.save()

        self.channel.notify(self.flip)

        self.assertEmailContainsText("Mon 2-29")
        self.assertEmailContainsHtml("<code>Mon 2-29</code>")
        self.assertEmailContains("Europe/Riga")

    def test_it_truncates_long_body(self) -> None:
        self.ping.body_raw = b"X" * 10000 + b", and the rest gets cut off"
        self.ping.save()

        self.channel.notify(self.flip)

        self.assertEmailContains("[truncated]")
        self.assertEmailNotContains("the rest gets cut off")

    def test_it_handles_missing_ping_object(self) -> None:
        self.ping.delete()

        self.channel.notify(self.flip)

        self.assertEmailContainsHtml("Daily Backup")

    def test_it_ignores_ping_after_flip(self) -> None:
        self.ping.created = self.flip.created + td(minutes=5)
        self.ping.save()

        self.channel.notify(self.flip)

        self.assertEmailNotContains("Last ping")
        self.assertEmailNotContains("Last Ping")

    def test_it_handles_identical_ping_and_flip_timestamp(self) -> None:
        self.ping.created = self.flip.created
        self.ping.save()

        self.channel.notify(self.flip)

        self.assertEmailContainsText("Last ping")
        self.assertEmailContainsHtml("Last Ping")

    def test_it_handles_missing_profile(self) -> None:
        self.channel.value = "alice+notifications@example.org"
        self.channel.save()

        self.channel.notify(self.flip)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice+notifications@example.org")

        self.assertEmailContains("Daily Backup")
        self.assertEmailNotContains("Projects Overview")

    def test_it_handles_json_value(self) -> None:
        payload = {"value": "alice@example.org", "up": True, "down": True}
        self.channel.value = json.dumps(payload)
        self.channel.save()

        self.channel.notify(self.flip)

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")

    def test_it_reports_unverified_email(self) -> None:
        self.channel.email_verified = False
        self.channel.save()

        self.channel.notify(self.flip)

        # If an email is not verified, it should say so in the notification:
        n = Notification.objects.get()
        self.assertEqual(n.error, "Email not verified")

    def test_it_checks_up_down_flags(self) -> None:
        payload = {"value": "alice@example.org", "up": True, "down": False}
        self.channel.value = json.dumps(payload)
        self.channel.save()

        self.channel.notify(self.flip)

        # This channel should not notify on "down" events:
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_it_handles_amperstand(self) -> None:
        self.check.name = "Foo & Bar"
        self.check.save()

        self.channel.notify(self.flip)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "DOWN | Foo & Bar")

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.get_object")
    def test_it_handles_pending_body(self, get_object: Mock) -> None:
        get_object.return_value = None

        self.ping.object_size = 1000
        self.ping.body_raw = None
        self.ping.save()

        with patch("hc.api.transports.time.sleep"):
            self.channel.notify(self.flip)

        self.assertEmailContains("The request body data is being processed")

    def test_it_shows_ignored_nonzero_exitstatus(self) -> None:
        self.ping.kind = "ign"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)

        self.assertEmailContains("Ignored")

    def test_it_handles_last_ping_log(self) -> None:
        self.ping.kind = "log"
        self.ping.save()

        self.channel.notify(self.flip)

        self.assertEmailContains("Log")

    def test_it_handles_last_ping_exitstatus(self) -> None:
        self.ping.kind = "fail"
        self.ping.exitstatus = 123
        self.ping.save()

        self.channel.notify(self.flip)

        self.assertEmailContains("Exit status 123")

    @override_settings(EMAIL_MAIL_FROM_TMPL="%s@bounces.example.org")
    def test_it_sets_custom_mail_from(self) -> None:
        self.channel.notify(self.flip)

        email = mail.outbox[0]
        self.assertTrue(email.from_email.startswith("n."))
        self.assertTrue(email.from_email.endswith("@bounces.example.org"))
        # The From header should contain the display address
        self.assertEqual(email.extra_headers["From"], settings.DEFAULT_FROM_EMAIL)
        # There should be no X-Bounce-ID header
        self.assertNotIn("X-Bounce-ID", email.extra_headers)

    @override_settings(DEFAULT_FROM_EMAIL="alerts@example.org")
    def test_it_displays_last_ping_subject(self) -> None:
        self.ping.scheme = "email"
        self.ping.body_raw = b"""Subject: Foo bar baz

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua.

"""
        self.ping.save()

        self.channel.notify(self.flip)

        self.assertEmailContains("Lorem ipsum")
        self.assertEmailContainsText("Last ping subject: Foo bar baz")
        self.assertEmailContainsHtml("<b>Last Ping Subject</b><br>Foo bar baz")
