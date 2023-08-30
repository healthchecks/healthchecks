from __future__ import annotations

from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class PingBodyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.ping = Ping.objects.create(owner=self.check, n=1, body_raw=b"this is body")
        self.url = f"/checks/{self.check.code}/pings/1/body/"

    def test_it_works(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.content, b"this is body")

    def test_it_requires_logged_in_user(self) -> None:
        r = self.client.get(self.url)
        self.assertRedirects(r, "/accounts/login/?next=" + self.url)

    def test_it_handles_missing_ping(self) -> None:
        self.ping.delete()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_body(self) -> None:
        self.ping.body_raw = None
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_allows_cross_team_access(self) -> None:
        Ping.objects.create(owner=self.check, body="this is body")

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_returns_original_bytes(self) -> None:
        self.ping.body_raw = b"Hello\x01\x99World"
        self.ping.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"Hello\x01\x99World")
