from hc.api.models import Check, Ping
from hc.test import BaseTestCase


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
