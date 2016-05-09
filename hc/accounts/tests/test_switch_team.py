from django.contrib.auth.models import User

from hc.test import BaseTestCase
from hc.accounts.models import Member, Profile


class SwitchTeamTestCase(BaseTestCase):

    def setUp(self):
        super(SwitchTeamTestCase, self).setUp()

        self.bob = User(username="bob", email="bob@example.org")
        self.bob.set_password("password")
        self.bob.save()

        bobs_profile = Profile(user=self.bob)
        bobs_profile.save()


        m = Member(team=bobs_profile, user=self.alice)
        m.save()

    def test_it_switches(self):
        self.client.login(username="alice@example.org", password="password")

        url = "/accounts/switch_team/%s/" % self.bob.username
        r = self.client.get(url, follow=True)

        self.assertContains(r, "bob@example.org")


    def test_it_checks_team_membership(self):
        self.client.login(username="charlie@example.org", password="password")

        url = "/accounts/switch_team/%s/" % self.bob.username
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)
