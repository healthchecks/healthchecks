from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class StatusTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check(project=self.project, name="Alice Was Here")
        self.check.tags = "foo"
        self.check.save()

        self.url = f"/projects/{self.project.code}/checks/status/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        doc = r.json()

        self.assertEqual(doc["tags"]["foo"], ["up", "1 up"])

        detail = doc["details"][0]
        self.assertEqual(detail["code"], str(self.check.code))
        self.assertEqual(detail["status"], "new")
        self.assertIn("Never", detail["last_ping"])

    def test_it_allows_cross_team_access(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_checks_ownership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
