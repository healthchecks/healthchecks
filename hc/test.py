from django.contrib.auth.models import User
from django.test import TestCase

from hc.accounts.models import Member, Profile


class BaseTestCase(TestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()

        # Alice is a normal user for tests. Alice has team access enabled.
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

        self.profile = Profile(user=self.alice, api_key="abc")
        self.profile.team_access_allowed = True
        self.profile.save()

        # Bob is on Alice's team and should have access to her stuff
        self.bob = User(username="bob", email="bob@example.org")
        self.bob.set_password("password")
        self.bob.save()

        self.bobs_profile = Profile(user=self.bob)
        self.bobs_profile.current_team = self.profile
        self.bobs_profile.save()

        m = Member(team=self.profile, user=self.bob)
        m.save()

        # Charlie should have no access to Alice's stuff
        self.charlie = User(username="charlie", email="charlie@example.org")
        self.charlie.set_password("password")
        self.charlie.save()

        ### Set Charles not to have access to Alice's stuff
