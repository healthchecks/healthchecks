from django.contrib.auth.models import User
from django.test import TestCase
from hc.api.models import Check


class RemoveCheckTestCase(TestCase):

    def setUp(self):
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

        self.check = Check(user=self.alice)
        self.check.save()

    def test_it_works(self):
        url = "/checks/%s/remove/" % self.check.code

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertRedirects(r, "/checks/")

        assert Check.objects.count() == 0

    def test_it_handles_bad_uuid(self):
        url = "/checks/not-uuid/remove/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        assert r.status_code == 400

    def test_it_checks_owner(self):
        url = "/checks/%s/remove/" % self.check.code

        mallory = User(username="mallory", email="mallory@example.org")
        mallory.set_password("password")
        mallory.save()

        self.client.login(username="mallory@example.org", password="password")
        r = self.client.post(url)
        assert r.status_code == 403

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/remove/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        assert r.status_code == 404
