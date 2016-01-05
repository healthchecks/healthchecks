from django.contrib.auth.models import User
from django.test import TestCase
from hc.api.models import Check


class AddCheckTestCase(TestCase):

    def setUp(self):
        super(AddCheckTestCase, self).setUp()
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

    def test_it_works(self):
        url = "/checks/add/"
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertRedirects(r, "/checks/")
        assert Check.objects.count() == 1
