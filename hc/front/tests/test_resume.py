from hc.api.models import Check
from hc.test import BaseTestCase


class ResumeTestCase(BaseTestCase):
    def setUp(self):
        super(ResumeTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project, status="paused")
        self.url = "/checks/%s/resume/" % self.check.code
        self.redirect_url = "/checks/%s/details/" % self.check.code

    def test_it_resumes(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "new")

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_allows_cross_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)
