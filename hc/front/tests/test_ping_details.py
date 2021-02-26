from hc.api.models import Check, Ping
from hc.test import BaseTestCase

PLAINTEXT_EMAIL = """Content-Type: multipart/alternative; boundary=bbb

--bbb
Content-Type: text/plain;charset=utf-8
Content-Transfer-Encoding: base64

aGVsbG8gd29ybGQ=

--bbb
"""

BAD_BASE64_EMAIL = """Content-Type: multipart/alternative; boundary=bbb

--bbb
Content-Type: text/plain;charset=utf-8
Content-Transfer-Encoding: base64

!!!

--bbb
"""

HTML_EMAIL = """Content-Type: multipart/alternative; boundary=bbb

--bbb
Content-Type: text/html;charset=utf-8
Content-Transfer-Encoding: base64

PGI+aGVsbG88L2I+

--bbb
"""


class PingDetailsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = "/checks/%s/last_ping/" % self.check.code

    def test_it_works(self):
        Ping.objects.create(owner=self.check, body="this is body")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "this is body", status_code=200)

    def test_it_requires_logged_in_user(self):
        Ping.objects.create(owner=self.check, body="this is body")

        r = self.client.get(self.url)
        self.assertRedirects(r, "/accounts/login/?next=" + self.url)

    def test_it_shows_fail(self):
        Ping.objects.create(owner=self.check, kind="fail")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "/fail", status_code=200)

    def test_it_shows_start(self):
        Ping.objects.create(owner=self.check, kind="start")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "/start", status_code=200)

    def test_it_accepts_n(self):
        # remote_addr, scheme, method, ua, body:
        self.check.ping("1.2.3.4", "http", "post", "tester", "foo-123", "success")
        self.check.ping("1.2.3.4", "http", "post", "tester", "bar-456", "success")

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/checks/%s/pings/1/" % self.check.code)
        self.assertContains(r, "foo-123", status_code=200)

        r = self.client.get("/checks/%s/pings/2/" % self.check.code)
        self.assertContains(r, "bar-456", status_code=200)

    def test_it_allows_cross_team_access(self):
        Ping.objects.create(owner=self.check, body="this is body")

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_missing_ping(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/%s/pings/123/" % self.check.code)
        self.assertContains(r, "No additional information is", status_code=200)

    def test_it_shows_nonzero_exitstatus(self):
        Ping.objects.create(owner=self.check, kind="fail", exitstatus=42)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "(failure, exit status 42)", status_code=200)

    def test_it_shows_zero_exitstatus(self):
        Ping.objects.create(owner=self.check, exitstatus=0)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "(exit status 0)", status_code=200)

    def test_it_decodes_plaintext_email_body(self):
        Ping.objects.create(owner=self.check, scheme="email", body=PLAINTEXT_EMAIL)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, "email-body-plain", status_code=200)
        self.assertNotContains(r, "email-body-html")

        # aGVsbG8gd29ybGQ= is base64("hello world")
        self.assertContains(r, "aGVsbG8gd29ybGQ=")
        self.assertContains(r, "hello world")

    def test_it_handles_bad_base64_in_email_body(self):
        Ping.objects.create(owner=self.check, scheme="email", body=BAD_BASE64_EMAIL)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertContains(r, "!!!", status_code=200)
        self.assertNotContains(r, "email-body-plain")
        self.assertNotContains(r, "email-body-html")

    def test_it_decodes_html_email_body(self):
        Ping.objects.create(owner=self.check, scheme="email", body=HTML_EMAIL)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, "email-body-plain", status_code=200)
        self.assertContains(r, "email-body-html")

        # PGI+aGVsbG88L2I+ is base64("<b>hello</b>")
        self.assertContains(r, "PGI+aGVsbG88L2I+")
        self.assertContains(r, "&lt;b&gt;hello&lt;/b&gt;")

    def test_it_decodes_email_subject(self):
        Ping.objects.create(
            owner=self.check,
            scheme="email",
            body="Subject: =?UTF-8?B?aGVsbG8gd29ybGQ=?=",
        )

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)

        # aGVsbG8gd29ybGQ= is base64("hello world")
        self.assertContains(r, "hello world", status_code=200)
