from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Check, Ping
from hc.test import BaseTestCase

PLAINTEXT_EMAIL = b"""Content-Type: multipart/alternative; boundary=bbb

--bbb
Content-Type: text/plain;charset=utf-8
Content-Transfer-Encoding: base64

aGVsbG8gd29ybGQ=

--bbb
"""

BAD_BASE64_EMAIL = b"""Content-Type: multipart/alternative; boundary=bbb

--bbb
Content-Type: text/plain;charset=utf-8
Content-Transfer-Encoding: base64

!!!

--bbb
"""

HTML_EMAIL = b"""Content-Type: multipart/alternative; boundary=bbb

--bbb
Content-Type: text/html;charset=utf-8
Content-Transfer-Encoding: base64

PGI+aGVsbG88L2I+

--bbb
"""


class PingDetailsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/checks/{self.check.code}/last_ping/"

    def test_it_works(self) -> None:
        Ping.objects.create(owner=self.check, n=1, body_raw=b"this is body")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "this is body", status_code=200)

    def test_it_displays_body(self) -> None:
        Ping.objects.create(owner=self.check, n=1, body="this is body")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "this is body", status_code=200)

    def test_it_displays_duration(self) -> None:
        expected_duration = td(minutes=5)
        end_time = now()
        start_time = end_time - expected_duration

        Ping.objects.create(owner=self.check, created=start_time, n=1, kind="start")
        Ping.objects.create(owner=self.check, created=end_time, n=2, kind="")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, "5 min 0 sec", status_code=200)

    def test_it_requires_logged_in_user(self) -> None:
        Ping.objects.create(owner=self.check, n=1, body="this is body")

        r = self.client.get(self.url)
        self.assertRedirects(r, "/accounts/login/?next=" + self.url)

    def test_it_shows_fail(self) -> None:
        Ping.objects.create(owner=self.check, n=1, kind="fail")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "/fail", status_code=200)

    def test_it_shows_start(self) -> None:
        Ping.objects.create(owner=self.check, n=1, kind="start")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(f"/checks/{self.check.code}/pings/1/")
        self.assertContains(r, "/start", status_code=200)

    def test_it_shows_log(self) -> None:
        Ping.objects.create(owner=self.check, n=1, kind="log")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(f"/checks/{self.check.code}/pings/1/")
        self.assertContains(r, "/log", status_code=200)

    def test_last_ping_lookup_excludes_log_ign_start(self) -> None:
        Ping.objects.create(owner=self.check, n=1)
        Ping.objects.create(owner=self.check, n=2, kind="log")
        Ping.objects.create(owner=self.check, n=3, kind="ign")
        Ping.objects.create(owner=self.check, n=4, kind="start")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "#1", status_code=200)

    def test_it_accepts_n(self) -> None:
        # remote_addr, scheme, method, ua, body, action, rid:
        self.check.ping(
            "1.2.3.4", "http", "post", "tester", b"foo-123", "success", None
        )
        self.check.ping(
            "1.2.3.4", "http", "post", "tester", b"bar-456", "success", None
        )

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(f"/checks/{self.check.code}/pings/1/")
        self.assertContains(r, "foo-123", status_code=200)

        r = self.client.get(f"/checks/{self.check.code}/pings/2/")
        self.assertContains(r, "bar-456", status_code=200)

    def test_it_allows_cross_team_access(self) -> None:
        Ping.objects.create(owner=self.check, n=1, body="this is body")

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_missing_ping(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/%s/pings/123/" % self.check.code)
        self.assertContains(r, "No additional information is", status_code=200)

    def test_it_shows_nonzero_exitstatus(self) -> None:
        Ping.objects.create(owner=self.check, n=1, kind="fail", exitstatus=42)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "(failure, exit status 42)", status_code=200)

    def test_it_shows_zero_exitstatus(self) -> None:
        Ping.objects.create(owner=self.check, n=1, exitstatus=0)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "(exit status 0)", status_code=200)

    def test_it_decodes_plaintext_email_body(self) -> None:
        Ping.objects.create(
            owner=self.check, n=1, scheme="email", body_raw=PLAINTEXT_EMAIL
        )

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, "email-body-plain", status_code=200)
        self.assertNotContains(r, "email-body-html")

        # aGVsbG8gd29ybGQ= is base64("hello world")
        self.assertContains(r, "aGVsbG8gd29ybGQ=")
        self.assertContains(r, "hello world")

    def test_it_decodes_plaintext_email_body_str(self) -> None:
        body = PLAINTEXT_EMAIL.decode()
        Ping.objects.create(owner=self.check, n=1, scheme="email", body=body)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        fragment = """<div id="email-body-plain" class="tab-pane active">"""
        self.assertContains(r, fragment, status_code=200)
        self.assertContains(r, "aGVsbG8gd29ybGQ=")
        self.assertContains(r, "hello world")

    def test_it_handles_bad_base64_in_email_body(self) -> None:
        Ping.objects.create(
            owner=self.check, n=1, scheme="email", body_raw=BAD_BASE64_EMAIL
        )

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, "!!!", status_code=200)
        self.assertNotContains(r, "email-body-plain")
        self.assertNotContains(r, "email-body-html")

    def test_it_decodes_html_email_body(self) -> None:
        Ping.objects.create(owner=self.check, n=1, scheme="email", body_raw=HTML_EMAIL)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, "email-body-plain", status_code=200)
        fragment = """<div id="email-body-html" class="tab-pane active">"""
        self.assertContains(r, fragment)

        # PGI+aGVsbG88L2I+ is base64("<b>hello</b>")
        self.assertContains(r, "PGI+aGVsbG88L2I+")
        self.assertContains(r, "&lt;b&gt;hello&lt;/b&gt;")

    def test_it_decodes_email_subject(self) -> None:
        Ping.objects.create(
            owner=self.check,
            n=1,
            scheme="email",
            body="Subject: =?UTF-8?B?aGVsbG8gd29ybGQ=?=",
        )

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        # aGVsbG8gd29ybGQ= is base64("hello world")
        self.assertContains(r, "hello world", status_code=200)

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.get_object")
    def test_it_loads_body_from_object_storage(self, get_object: Mock) -> None:
        Ping.objects.create(owner=self.check, n=1, object_size=1000)
        get_object.return_value = b"dummy body from object storage"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "dummy body from object storage", status_code=200)

        code, n = get_object.call_args.args
        self.assertEqual(code, str(self.check.code))
        self.assertEqual(n, 1)

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.get_object")
    def test_it_decodes_plaintext_email_from_object_storage(
        self, get_object: Mock
    ) -> None:
        Ping.objects.create(owner=self.check, n=1, scheme="email", object_size=1000)
        get_object.return_value = PLAINTEXT_EMAIL

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        # It should call get_object only once
        self.assertEqual(get_object.call_count, 1)

        self.assertContains(r, "email-body-plain", status_code=200)
        self.assertNotContains(r, "email-body-html")

        # aGVsbG8gd29ybGQ= is base64("hello world")
        self.assertContains(r, "aGVsbG8gd29ybGQ=")
        self.assertContains(r, "hello world")

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.get_object")
    def test_it_handles_missing_object(self, get_object: Mock) -> None:
        Ping.objects.create(owner=self.check, n=1, object_size=1000)
        get_object.return_value = None

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "please check back later", status_code=200)

    @override_settings(S3_BUCKET="test-bucket")
    @patch("hc.api.models.get_object")
    def test_it_handles_missing_object_email(self, get_object: Mock) -> None:
        Ping.objects.create(owner=self.check, n=1, scheme="email", object_size=1000)
        get_object.return_value = None

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "please check back later", status_code=200)

    @override_settings(S3_BUCKET=None)
    def test_it_handles_missing_s3_credentials(self) -> None:
        Ping.objects.create(owner=self.check, n=1, object_size=1000)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "please check back later", status_code=200)

    def test_it_shows_ignored_nonzero_exitstatus(self) -> None:
        Ping.objects.create(owner=self.check, n=1, kind="ign", exitstatus=42)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(f"/checks/{self.check.code}/pings/1/")
        self.assertContains(r, "(ignored)", status_code=200)
