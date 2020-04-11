from hc.api.models import Check
from hc.test import BaseTestCase


class RemoveCheckTestCase(BaseTestCase):
    def setUp(self):
        super(RemoveCheckTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project)
        self.remove_url = "/checks/%s/remove/" % self.check.code
        self.redirect_url = "/projects/%s/checks/" % self.project.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.remove_url)
        self.assertRedirects(r, self.redirect_url)

        self.assertEqual(Check.objects.count(), 0)

    def test_team_access_works(self):
        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.remove_url)

        self.assertEqual(Check.objects.count(), 0)

    def test_it_handles_bad_uuid(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/checks/not-uuid/remove/")
        self.assertEqual(r.status_code, 404)

    def test_it_checks_owner(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.remove_url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self):
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/remove/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.remove_url)
        self.assertEqual(r.status_code, 405)

    def test_it_allows_cross_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.remove_url)
        self.assertRedirects(r, self.redirect_url)
