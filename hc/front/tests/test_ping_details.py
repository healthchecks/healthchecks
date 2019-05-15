from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class LastPingTestCase(BaseTestCase):
    def test_it_works(self):
        check = Check.objects.create(project=self.project)
        Ping.objects.create(owner=check, body="this is body")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/%s/last_ping/" % check.code)
        self.assertContains(r, "this is body", status_code=200)

    def test_it_shows_fail(self):
        check = Check.objects.create(project=self.project)
        Ping.objects.create(owner=check, kind="fail")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/%s/last_ping/" % check.code)
        self.assertContains(r, "/fail", status_code=200)

    def test_it_shows_start(self):
        check = Check.objects.create(project=self.project)
        Ping.objects.create(owner=check, kind="start")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/checks/%s/last_ping/" % check.code)
        self.assertContains(r, "/start", status_code=200)

    def test_it_accepts_n(self):
        check = Check.objects.create(project=self.project)

        # remote_addr, scheme, method, ua, body:
        check.ping("1.2.3.4", "http", "post", "tester", "foo-123", "success")
        check.ping("1.2.3.4", "http", "post", "tester", "bar-456", "success")

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/checks/%s/pings/1/" % check.code)
        self.assertContains(r, "foo-123", status_code=200)

        r = self.client.get("/checks/%s/pings/2/" % check.code)
        self.assertContains(r, "bar-456", status_code=200)

    def test_it_allows_cross_team_access(self):
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        check = Check.objects.create(project=self.project)
        Ping.objects.create(owner=check, body="this is body")

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get("/checks/%s/last_ping/" % check.code)
        self.assertEqual(r.status_code, 200)
