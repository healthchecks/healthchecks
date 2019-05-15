from django.contrib.auth.models import User
from django.test import TestCase

from hc.accounts.models import Member, Profile, Project


class BaseTestCase(TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()

        # Alice is a normal user for tests. Alice has team access enabled.
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

        self.project = Project(owner=self.alice, api_key="X" * 32)
        self.project.name = "Alice's Project"
        self.project.badge_key = self.alice.username
        self.project.save()

        self.profile = Profile(user=self.alice)
        self.profile.sms_limit = 50
        self.profile.current_project = self.project
        self.profile.save()

        # Bob is on Alice's team and should have access to her stuff
        self.bob = User(username="bob", email="bob@example.org")
        self.bob.set_password("password")
        self.bob.save()

        self.bobs_project = Project(owner=self.bob)
        self.bobs_project.badge_key = self.bob.username
        self.bobs_project.save()

        self.bobs_profile = Profile(user=self.bob)
        self.bobs_profile.current_project = self.project
        self.bobs_profile.save()

        Member.objects.create(user=self.bob, project=self.project)

        # Charlie should have no access to Alice's stuff
        self.charlie = User(username="charlie", email="charlie@example.org")
        self.charlie.set_password("password")
        self.charlie.save()

        self.charlies_project = Project(owner=self.charlie)
        self.charlies_project.badge_key = self.charlie.username
        self.charlies_project.save()

        self.charlies_profile = Profile(user=self.charlie)
        self.charlies_profile.current_project = self.charlies_project
        self.charlies_profile.save()
