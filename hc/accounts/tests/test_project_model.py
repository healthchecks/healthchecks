from hc.test import BaseTestCase
from hc.accounts.models import Member, Project
from hc.api.models import Check, Channel


class ProjectModelTestCase(BaseTestCase):
    def test_num_checks_available_handles_multiple_projects(self):
        # One check in Alice's primary project:
        Check.objects.create(project=self.project)

        # One check in Alice's secondary project:
        p2 = Project.objects.create(owner=self.alice)
        Check.objects.create(project=p2)

        self.assertEqual(self.project.num_checks_available(), 18)

    def test_it_handles_zero_broken_channels(self):
        Channel.objects.create(kind="webhook", last_error="", project=self.project)

        self.assertFalse(self.project.have_channel_issues())

    def test_it_handles_one_broken_channel(self):
        Channel.objects.create(kind="webhook", last_error="x", project=self.project)

        self.assertTrue(self.project.have_channel_issues())

    def test_it_handles_no_channels(self):
        # It's an issue if the project has no channels at all:
        self.assertTrue(self.project.have_channel_issues())

    def test_it_allows_third_user(self):
        # Alice is the owner, and Bob is invited -- there is space for the third user:
        self.assertTrue(self.project.can_invite_new_users())

    def test_it_allows_same_user_in_multiple_projects(self):
        p2 = Project.objects.create(owner=self.alice)
        Member.objects.create(user=self.bob, project=p2)

        # Bob's membership in two projects counts as one seat,
        # one seat should be still free:
        self.assertTrue(self.project.can_invite_new_users())

    def test_it_checks_team_limit(self):
        p2 = Project.objects.create(owner=self.alice)
        Member.objects.create(user=self.charlie, project=p2)

        # Alice and Bob are in one project, Charlie is in another,
        # so no seats left:
        self.assertFalse(self.project.can_invite_new_users())
