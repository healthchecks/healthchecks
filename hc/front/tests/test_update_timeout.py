from django.contrib.auth.models import User
from django.test import TestCase

from hc.api.models import Check


class UpdateTimeoutTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.check = Check(user=self.alice)
        self.check.save()

    def test_it_works(self):
        url = "/checks/%s/timeout/" % self.check.code
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="alice", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 302

        check = Check.objects.get(code=self.check.code)
        assert check.timeout.total_seconds() == 3600
        assert check.grace.total_seconds() == 60

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/timeout/"
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="alice", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 400
