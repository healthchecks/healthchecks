from hc.api.models import Check
from hc.test import BaseTestCase


class AddCheckTestCase(BaseTestCase):
    def setUp(self):
        super(AddCheckTestCase, self).setUp()

        self.url = "/projects/%s/checks/add/" % self.project.code
        self.redirect_url = "/projects/%s/checks/" % self.project.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)

        redirect_url = "/checks/%s/details/?new" % check.code
        self.assertRedirects(r, redirect_url)

    def test_it_handles_unset_current_project(self):
        self.profile.current_project = None
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)

        redirect_url = "/checks/%s/details/?new" % check.code
        self.assertRedirects(r, redirect_url)

    def test_team_access_works(self):
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url)

        check = Check.objects.get()
        # Added by bob, but should belong to alice (bob has team access)
        self.assertEqual(check.project, self.project)

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_obeys_check_limit(self):
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 400)
