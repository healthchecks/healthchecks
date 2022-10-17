from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class UncloakTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project, status="paused")
        self.url = "/cloaked/%s/" % self.check.unique_key
        self.redirect_url = "/checks/%s/details/" % self.check.code

    def test_it_redirects(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertRedirects(r, self.redirect_url)

    def test_it_handles_bad_unique_key(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/cloaked/0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33/")
        self.assertEqual(r.status_code, 404)

    def test_it_checks_access(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_logged_in_user(self):
        r = self.client.get(self.url)
        self.assertRedirects(r, "/accounts/login/?next=" + self.url)
