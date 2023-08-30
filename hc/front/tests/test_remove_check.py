from __future__ import annotations

from hc.api.models import Check
from hc.test import BaseTestCase


class RemoveCheckTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.remove_url = f"/checks/{self.check.code}/remove/"
        self.redirect_url = f"/projects/{self.project.code}/checks/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.remove_url)
        self.assertRedirects(r, self.redirect_url)

        self.assertEqual(Check.objects.count(), 0)

    def test_team_access_works(self) -> None:
        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.remove_url)

        self.assertEqual(Check.objects.count(), 0)

    def test_it_handles_bad_uuid(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/checks/not-uuid/remove/")
        self.assertEqual(r.status_code, 404)

    def test_it_checks_owner(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.remove_url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self) -> None:
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/remove/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.remove_url)
        self.assertEqual(r.status_code, 405)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.remove_url)
        self.assertEqual(r.status_code, 403)
