from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class RemoveProjectTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.url = "/projects/%s/remove/" % self.project.code

    def test_it_works(self) -> None:
        Check.objects.create(project=self.project, tags="foo a-B_1  baz@")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, "/")

        # Alice should not own any projects
        self.assertFalse(self.alice.project_set.exists())

        # Check should be gone
        self.assertFalse(Check.objects.exists())

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_checks_access(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 404)
