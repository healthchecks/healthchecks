from django.contrib.auth.models import User
from django.test import TestCase
from hc.api.models import Check, Ping


class LogTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

        self.check = Check(user=self.alice)
        self.check.save()

        ping = Ping(owner=self.check)
        ping.save()

    def test_it_works(self):
        url = "/checks/%s/log/" % self.check.code

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertContains(r, "Dates and times are", status_code=200)

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
        charlie = User(username="charlie", email="charlie@example.org")
        charlie.set_password("password")
        charlie.save()

        url = "/checks/%s/log/" % self.check.code
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(url)
        assert r.status_code == 403
