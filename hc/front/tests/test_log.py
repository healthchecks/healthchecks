from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class LogTestCase(BaseTestCase):

    def setUp(self):
        super(LogTestCase, self).setUp()
        self.check = Check(user=self.alice)
        self.check.save()

        ping = Ping(owner=self.check)
        ping.save()

    def test_it_works(self):
        url = "/checks/%s/log/" % self.check.code

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertContains(r, "Local Time", status_code=200)

    def test_team_access_works(self):
        url = "/checks/%s/log/" % self.check.code

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/log/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        assert r.status_code == 400

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/log/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        assert r.status_code == 404

    def test_it_checks_ownership(self):
        url = "/checks/%s/log/" % self.check.code
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(url)
        assert r.status_code == 403
