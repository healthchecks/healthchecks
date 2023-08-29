from __future__ import annotations

from hc.accounts.models import Project
from hc.test import BaseTestCase


class AddProjectTestCase(BaseTestCase):
    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/projects/add/", {"name": "My Second Project"})

        p = Project.objects.get(owner=self.alice, name="My Second Project")
        self.assertRedirects(r, "/projects/%s/checks/" % p.code)
        self.assertEqual(str(p.code), p.badge_key)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/projects/add/")
        self.assertEqual(r.status_code, 405)
