from django.contrib.auth.models import User
from django.test import TestCase

from hc.accounts.models import Profile


class BaseTestCase(TestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()

        # Normal user for tests
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

        self.profile = Profile(user=self.alice, api_key="abc")
        self.profile.save()

        # "malicious user for tests
        self.charlie = User(username="charlie", email="charlie@example.org")
        self.charlie.set_password("password")
        self.charlie.save()

        charlies_profile = Profile(user=self.charlie)
        charlies_profile.save()
