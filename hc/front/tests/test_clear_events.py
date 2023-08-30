from __future__ import annotations

from django.utils.timezone import now

from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class ClearEventsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.check.last_ping = now()
        self.check.n_pings = 1
        self.check.save()

        Ping.objects.create(owner=self.check, n=1)

        self.clear_url = f"/checks/{self.check.code}/clear_events/"
        self.redirect_url = f"/checks/{self.check.code}/details/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.clear_url)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertIsNone(self.check.last_ping)
        self.assertFalse(self.check.ping_set.exists())

    def test_team_access_works(self) -> None:
        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.clear_url)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertIsNone(self.check.last_ping)

    def test_it_handles_bad_uuid(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/checks/not-uuid/clear_events/")
        self.assertEqual(r.status_code, 404)

    def test_it_checks_owner(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.clear_url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self) -> None:
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/clear_events/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(url)
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.clear_url)
        self.assertEqual(r.status_code, 405)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.clear_url)
        self.assertEqual(r.status_code, 403)
