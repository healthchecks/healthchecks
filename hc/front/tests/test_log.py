from django.contrib.auth.models import User
from django.test import TestCase

from hc.api.models import Check


class LogTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.check = Check(user=self.alice)
        self.check.save()

    def test_it_works(self):
        url = "/checks/%s/log/" % self.check.code

        self.client.login(username="alice", password="password")
        r = self.client.get(url)
        self.assertContains(r, "Log for", status_code=200)

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/log/"

        self.client.login(username="alice", password="password")
        r = self.client.get(url)
        assert r.status_code == 400

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/log/"

        self.client.login(username="alice", password="password")
        r = self.client.get(url)
        assert r.status_code == 404
