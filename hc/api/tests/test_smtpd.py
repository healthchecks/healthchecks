from hc.api.models import Check, Ping
from hc.test import BaseTestCase
from hc.api.management.commands.smtpd import _process_message


PAYLOAD_TMPL = """
From: "User Name" <username@gmail.com>
To: "John Smith" <john@example.com>
Subject: %s

...
""".strip()


class SmtpdTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.email = "%s@does.not.matter" % self.check.code

    def test_it_works(self):
        _process_message("1.2.3.4", "foo@example.org", self.email, b"hello world")

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.body, "hello world")
        self.assertEqual(ping.kind, None)

    def test_it_handles_subject_filter_match(self):
        self.check.subject = "SUCCESS"
        self.check.save()

        body = PAYLOAD_TMPL % "[SUCCESS] Backup completed"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, None)

    def test_it_handles_subject_filter_miss(self):
        self.check.subject = "SUCCESS"
        self.check.save()

        body = PAYLOAD_TMPL % "[FAIL] Backup did not complete"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "ign")

    def test_it_handles_subject_fail_filter_match(self):
        self.check.subject_fail = "FAIL"
        self.check.save()

        body = PAYLOAD_TMPL % "[FAIL] Backup did not complete"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "fail")

    def test_it_handles_subject_fail_filter_miss(self):
        self.check.subject_fail = "FAIL"
        self.check.save()

        body = PAYLOAD_TMPL % "[SUCCESS] Backup completed"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "ign")

    def test_it_handles_multiple_subject_keywords(self):
        self.check.subject = "SUCCESS, OK"
        self.check.save()

        body = PAYLOAD_TMPL % "[OK] Backup completed"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, None)

    def test_it_handles_multiple_subject_fail_keywords(self):
        self.check.subject_fail = "FAIL, WARNING"
        self.check.save()

        body = PAYLOAD_TMPL % "[WARNING] Backup did not complete"
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, "fail")

    def test_it_handles_encoded_subject(self):
        self.check.subject = "SUCCESS"
        self.check.save()

        body = PAYLOAD_TMPL % "=?US-ASCII?B?W1NVQ0NFU1NdIEJhY2t1cCBjb21wbGV0ZWQ=?="
        _process_message("1.2.3.4", "foo@example.org", self.email, body.encode("utf8"))

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "email")
        self.assertEqual(ping.ua, "Email from foo@example.org")
        self.assertEqual(ping.kind, None)
