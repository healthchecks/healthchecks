from django.contrib.auth.models import User
from django.test import TestCase

from hc.api.models import Check


class UpdateNameTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.check = Check(user=self.alice)
        self.check.save()

    def test_it_works(self):
        url = "/checks/%s/name/" % self.check.code
        payload = {"name": "Alice Was Here"}

        self.client.login(username="alice", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 302

        check = Check.objects.get(code=self.check.code)
        assert check.name == "Alice Was Here"

    def test_it_checks_ownership(self):

        charlie = User(username="charlie")
        charlie.set_password("password")
        charlie.save()

        url = "/checks/%s/name/" % self.check.code
        payload = {"name": "Charlie Sent This"}

        self.client.login(username="charlie", password="password")
        r = self.client.post(url, data=payload)
        assert r.status_code == 403
