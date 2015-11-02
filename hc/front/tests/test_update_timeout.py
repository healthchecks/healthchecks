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

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/timeout/"
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="alice", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 404

    def test_it_checks_ownership(self):
        charlie = User(username="charlie")
        charlie.set_password("password")
        charlie.save()

        url = "/checks/%s/timeout/" % self.check.code
        payload = {"timeout": 3600, "grace": 60}

        self.client.login(username="charlie", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 403
