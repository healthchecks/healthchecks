from hc.test import BaseTestCase
from hc.api.models import Check


class SwitchTeamTestCase(BaseTestCase):
    def setUp(self):
        super(SwitchTeamTestCase, self).setUp()

        self.url = "/accounts/switch_project/%s/" % self.project.code

    def test_it_switches(self):
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        c = Check(project=self.project, name="This belongs to Alice")
        c.save()

        self.client.login(username="bob@example.org", password="password")

        r = self.client.get(self.url, follow=True)

        self.assertContains(r, "This belongs to Alice")

        self.bobs_profile.refresh_from_db()
        self.assertEqual(self.bobs_profile.current_project, self.project)

    def test_it_checks_team_membership(self):
        self.client.login(username="charlie@example.org", password="password")

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_switches_to_own_team(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url, follow=True)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_invalid_project_code(self):
        self.client.login(username="bob@example.org", password="password")

        url = "/accounts/switch_project/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_login(self):
        r = self.client.get(self.url)

        expected_url = "/accounts/login/?next=" + self.url
        self.assertRedirects(r, expected_url)
