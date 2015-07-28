from django.contrib.auth.models import User
from django.test import TestCase

from hc.api.models import Check


class RemoveTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.check = Check(user=self.alice)
        self.check.save()

    def test_it_works(self):
        url = "/checks/%s/remove/" % self.check.code

        self.client.login(username="alice", password="password")
        r = self.client.post(url)
        assert r.status_code == 302

        assert Check.objects.count() == 0

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/remove/"

        self.client.login(username="alice", password="password")
        r = self.client.post(url)
        assert r.status_code == 400
