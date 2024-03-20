from __future__ import annotations

from django.utils.timezone import now

from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class LogTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.check.created = "2000-01-01T00:00:00+00:00"
        self.check.save()

        self.ping = Ping.objects.create(owner=self.check, n=1)
        self.ping.body_raw = b"hello world"

        # Older MySQL versions don't store microseconds. This makes sure
        # the ping is older than any notifications we may create later:
        self.ping.created = "2000-01-01T00:00:00+00:00"
        self.ping.save()

        self.url = f"/checks/{self.check.code}/log_events/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?success=on")
        self.assertContains(r, "hello world")

    def test_team_access_works(self) -> None:
        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_handles_bad_uuid(self) -> None:
        url = "/checks/not-uuid/log_events/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_uuid(self) -> None:
        # Valid UUID but there is no check for it:
        url = "/checks/6837d6ec-fc08-4da5-a67f-08a9ed1ccf62/log_events/"

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_it_checks_ownership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_accepts_start_parameter(self) -> None:
        ts = str(now().timestamp())
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?success=on&u=" + ts)
        self.assertNotContains(r, "hello world")

    def test_it_rejects_bad_u_parameter(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        for sample in ["surprise", "100000000000000000"]:
            r = self.client.get(self.url + "?u=" + sample)
            self.assertEqual(r.status_code, 400)
