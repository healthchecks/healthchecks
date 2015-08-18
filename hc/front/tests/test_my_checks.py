from django.contrib.auth.models import User
from django.test import TestCase

from hc.api.models import Check


class MyChecksTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice")
        self.alice.set_password("password")
        self.alice.save()

        self.check = Check(user=self.alice, name="Alice Was Here")
        self.check.save()

    def test_it_works(self):
        self.client.login(username="alice", password="password")
        r = self.client.get("/checks/")
        self.assertContains(r, "Alice Was Here", status_code=200)
