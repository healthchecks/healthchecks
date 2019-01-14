from hc.test import BaseTestCase
from hc.api.models import Check


class SwitchTeamTestCase(BaseTestCase):

    def test_it_switches(self):
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        c = Check(user=self.alice, name="This belongs to Alice",
                  project=self.project)
        c.save()

        self.client.login(username="bob@example.org", password="password")

        url = "/accounts/switch_team/%s/" % self.alice.username
        r = self.client.get(url, follow=True)

        self.assertContains(r, "This belongs to Alice")

        self.bobs_profile.refresh_from_db()
        self.assertEqual(self.bobs_profile.current_project, self.project)

    def test_it_checks_team_membership(self):
        self.client.login(username="charlie@example.org", password="password")

        url = "/accounts/switch_team/%s/" % self.alice.username
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

    def test_it_switches_to_own_team(self):
        self.client.login(username="alice@example.org", password="password")

        url = "/accounts/switch_team/%s/" % self.alice.username
        r = self.client.get(url, follow=True)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_invalid_username(self):
        self.client.login(username="bob@example.org", password="password")

        url = "/accounts/switch_team/dave/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

    def test_it_requires_login(self):
        url = "/accounts/switch_team/%s/" % self.alice.username
        r = self.client.get(url)

        expected_url = "/accounts/login/?next=/accounts/switch_team/alice/"
        self.assertRedirects(r, expected_url)
