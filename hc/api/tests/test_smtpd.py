from __future__ import annotations

from unittest.mock import Mock

from django.test.utils import override_settings

from hc.api.management.commands.smtpd import PingHandler, _process_message
from hc.api.models import Check, Ping
from hc.test import BaseTestCase

PAYLOAD_TMPL = """
From: "User Name" <username@gmail.com>
To: "John Smith" <john@example.com>
Subject: %s

...
""".strip()

HTML_PAYLOAD_TMPL = """
From: "User Name" <username@gmail.com>
To: "John Smith" <john@example.com>
Subject: %s
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="marker"

--marker
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 7bit

Plain text here

--marker
Content-Type: text/html; charset=utf-8
Content-Transfer-Encoding: 8bit

%s

--marker--
""".strip()


@override_settings(S3_BUCKET=None)
class SmtpdTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.email = "%s@does.not.matter" % self.check.code

    def test_it_works(self) -> None:
        _process_message("1.2.3.4", "foo@example.org", self.email, b"hello world")

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        assert ping.body_raw
        self.assertEqual(bytes(ping.body_raw), b"hello world")
        self.assertEqual(ping.kind, None)

    def test_it_handles_success_filter_match(self) -> None:
        self.check.filter_subject = True
        self.check.success_kw = "SUCCESS"
        self.check.save()

        body = PAYLOAD_TMPL % "[SUCCESS] Backup completed"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, None)

    def test_it_handles_success_filter_match_in_body(self) -> None:
        self.check.filter_body = True
        self.check.success_kw = "SUCCESS"
        self.check.save()

        body = PAYLOAD_TMPL % "Subject goes here"
        body += "\nBody goes here, SUCCESS.\n"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.kind, None)

    def test_it_handles_success_body_filter_match_in_html_body(self) -> None:
        self.check.filter_body = True
        self.check.success_kw = "SUCCESS"
        self.check.save()

        body = HTML_PAYLOAD_TMPL % ("Subject", "<b>S</b>UCCESS")
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.kind, None)

    def test_it_handles_success_filter_miss(self) -> None:
        self.check.filter_body = True
        self.check.success_kw = "SUCCESS"
        self.check.save()

        body = PAYLOAD_TMPL % "Subject goes here"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.kind, "ign")

    def test_it_handles_failure_filter_match(self) -> None:
        self.check.filter_subject = True
        self.check.failure_kw = "FAIL"
        self.check.save()

        body = PAYLOAD_TMPL % "[FAIL] Backup did not complete"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "fail")

    def test_it_handles_failure_filter_miss(self) -> None:
        self.check.filter_subject = True
        self.check.failure_kw = "FAIL"
        self.check.save()

        body = PAYLOAD_TMPL % "[SUCCESS] Backup completed"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "ign")

    def test_it_handles_multiple_success_keywords(self) -> None:
        self.check.filter_subject = True
        self.check.success_kw = "SUCCESS, OK"
        self.check.save()

        body = PAYLOAD_TMPL % "[OK] Backup completed"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, None)

    def test_it_handles_multiple_failure_keywords(self) -> None:
        self.check.filter_subject = True
        self.check.failure_kw = "FAIL, WARNING"
        self.check.save()

        body = PAYLOAD_TMPL % "[WARNING] Backup did not complete"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "fail")

    def test_it_handles_failure_before_success(self) -> None:
        self.check.filter_subject = True
        self.check.success_kw = "SUCCESS"
        self.check.failure_kw = "FAIL"
        self.check.save()

        subject = "[SUCCESS] 1 Backup completed, [FAIL] 1 Backup did not complete"
        body = PAYLOAD_TMPL % subject
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "fail")

    def test_it_handles_start_filter_match(self) -> None:
        self.check.filter_subject = True
        self.check.start_kw = "START"
        self.check.save()

        body = PAYLOAD_TMPL % "[START] Starting backup..."
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "start")

    def test_it_handles_encoded_subject(self) -> None:
        self.check.filter_subject = True
        self.check.success_kw = "SUCCESS"
        self.check.save()

        body = PAYLOAD_TMPL % "=?US-ASCII?B?W1NVQ0NFU1NdIEJhY2t1cCBjb21wbGV0ZWQ=?="
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, None)

    async def test_it_handles_multiple_recipients(self) -> None:
        class Session:
            peer = ["1.2.3.4"]

        class Envelope:
            mail_from = "foo@example.org"
            rcpt_tos = ["bar@example.org", self.email]
            content = b"hello world"

        class NullSink:
            def write(self, text: str) -> None:
                pass

        handler = PingHandler(NullSink())
        await handler.handle_DATA(Mock(), Session(), Envelope())

        ping = await Ping.objects.alatest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        assert ping.body_raw
        self.assertEqual(bytes(ping.body_raw), b"hello world")
        self.assertEqual(ping.kind, None)
