from __future__ import annotations

import time
from datetime import timedelta as td
from unittest.mock import patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Channel, Check, Notification
from hc.lib.signing import sign_bounce_id
from hc.test import BaseTestCase


class BounceTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check(project=self.project, status="up")
        self.check.save()

        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.email_verified = True
        self.channel.save()

        self.n = Notification(owner=self.check, channel=self.channel)
        self.n.save()

        self.url = "/api/v2/bounces/"

    def post(self, status="5.0.0", to_local=None):
        if to_local is None:
            to_local = sign_bounce_id("n.%s" % self.n.code)

        msg = f"""Subject: Undelivered Mail Returned to Sender
To: {to_local}@example.org
Content-Type: multipart/report; report-type=delivery-status;
 boundary=e8ed4343d6876891e609b8b58c7e77c88887386efa98970174bb7a6c29a0

--e8ed4343d6876891e609b8b58c7e77c88887386efa98970174bb7a6c29a0
Content-Description: Notification
Content-Type: text/plain; charset="utf-8"


Hello.

--e8ed4343d6876891e609b8b58c7e77c88887386efa98970174bb7a6c29a0
Content-Description: Delivery report
Content-Type: message/delivery-status

Reporting-Mta: dns; example.com

Status: {status}
Action: failed


--e8ed4343d6876891e609b8b58c7e77c88887386efa98970174bb7a6c29a0
Content-Transfer-Encoding: 8bit
Content-Type: message/rfc822-headers
Content-Description: Undelivered message header

To: foo@example.com


--e8ed4343d6876891e609b8b58c7e77c88887386efa98970174bb7a6c29a0--
"""

        return self.csrf_client.post(self.url, msg, content_type="text/plain")

    def test_it_handles_permanent_notification_bounce(self):
        r = self.post()
        self.assertEqual(r.status_code, 200)

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "Delivery failed (SMTP status code: 5.0.0)")
        self.assertEqual(r.content.decode(), "OK")

        self.channel.refresh_from_db()
        self.assertEqual(
            self.channel.last_error, "Delivery failed (SMTP status code: 5.0.0)"
        )
        self.assertTrue(self.channel.disabled)

    def test_it_handles_transient_notification_bounce(self):
        r = self.post(status="4.0.0")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "OK")

        self.n.refresh_from_db()
        self.assertEqual(self.n.error, "Delivery failed (SMTP status code: 4.0.0)")

        self.channel.refresh_from_db()
        self.assertEqual(
            self.channel.last_error, "Delivery failed (SMTP status code: 4.0.0)"
        )
        self.assertFalse(self.channel.disabled)

    def test_it_handles_notification_non_bounce(self):
        r = self.post(status="2.0.0")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "OK (ignored)")

    def test_it_handles_bad_signature(self):
        with override_settings(SECRET_KEY="wrong-signing-key"):
            to_local = sign_bounce_id("n.%s" % self.n.code)

        r = self.post(to_local=to_local)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "OK (bad signature)")

    def test_it_handles_expired_signature(self):
        with patch("hc.lib.signing.time") as mock_time:
            mock_time.time.return_value = time.time() - 3600 * 48 - 1
            to_local = sign_bounce_id("n.%s" % self.n.code)

        r = self.post(to_local=to_local)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "OK (bad signature)")

    def test_it_checks_notification_age(self):
        self.n.created = now() - td(hours=49)
        self.n.save()
        r = self.post()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "OK (notification not found)")

    def test_it_handles_permanent_report_bounce(self):
        to_local = sign_bounce_id("r.alice")
        r = self.post(to_local=to_local)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "OK")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reports, "off")
        self.assertEqual(self.profile.nag_period, td())

    def test_it_handles_transient_report_bounce(self):
        to_local = sign_bounce_id("r.alice")
        r = self.post(status="4.0.0", to_local=to_local)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "OK")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.reports, "monthly")

    def test_it_handles_bad_username(self):
        to_local = sign_bounce_id("r.doesnotexist")
        r = self.post(to_local=to_local)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode(), "OK (user not found)")
