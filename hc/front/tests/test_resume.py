from __future__ import annotations

from hc.api.models import Check, Flip
from hc.test import BaseTestCase


class ResumeTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project, status="paused")
        self.url = "/checks/%s/resume/" % self.check.code
        self.redirect_url = "/checks/%s/details/" % self.check.code

    def test_it_resumes(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "new")

        flip = Flip.objects.get()
        self.assertEqual(flip.old_status, "paused")
        self.assertEqual(flip.new_status, "new")
        # should be marked as processed from the beginning, so sendalerts ignores it
        self.assertTrue(flip.processed)

    def test_it_handles_not_paused_tests(self):
        self.check.status = "down"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 400)

        # The status should be unchanged
        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "down")

        # There should be no Flip object
        self.assertFalse(Flip.objects.exists())

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_allows_cross_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

    def test_it_requires_rw_access(self):
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)
