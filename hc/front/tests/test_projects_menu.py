from __future__ import annotations

from hc.test import BaseTestCase


class ProjectsMenuTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.url = "/projects/menu/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.assertContains(r, "Alices Project")
        self.assertContains(r, "status ic-up")

    def test_it_requires_logged_in_user(self) -> None:
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
