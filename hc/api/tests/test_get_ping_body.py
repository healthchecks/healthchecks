from __future__ import annotations

from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class GetPingBodyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.check = Check(project=self.project, name="Alice 1")
        self.check.n_pings = 1
        self.check.status = "up"
        self.check.save()

        self.ping = Ping(owner=self.check)
        self.ping.n = 1
        self.ping.body_raw = b"Foo\nBar\nBaz"
        self.ping.save()

        self.url = f"/api/v1/checks/{self.check.code}/pings/1/body"

    def test_it_works(self) -> None:
        r = self.client.get(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["Content-Type"], "text/plain")
        self.assertEqual(r.content, b"Foo\nBar\nBaz")

    def test_it_handles_missing_api_key(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(r, "missing api key", status_code=401)

    def test_readonly_key_is_not_allowed(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.client.get(self.url, HTTP_X_API_KEY="R" * 32)
        self.assertEqual(r.status_code, 401)

    def test_it_rejects_post(self) -> None:
        r = self.client.post(self.url, HTTP_X_API_KEY=self.project.api_key)
        self.assertEqual(r.status_code, 405)

    def test_it_rejects_charlies_key(self) -> None:
        self.charlies_project.api_key = "C" * 32
        self.charlies_project.save()

        r = self.client.get(self.url, HTTP_X_API_KEY="C" * 32)
        self.assertEqual(r.status_code, 403)

    def test_it_checks_n_threshold(self) -> None:
        self.check.n_pings = 101
        self.check.save()

        # The default ping log limit is 100, so the ping #1 is now outside the limit
        r = self.client.get(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_no_body(self) -> None:
        self.ping.body_raw = None
        self.ping.save()

        r = self.client.get(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 404)

    def test_it_returns_original_bytes(self) -> None:
        self.ping.body_raw = b"Hello\x01\x99World"
        self.ping.save()

        r = self.client.get(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["Content-Type"], "text/plain")
        self.assertEqual(r.content, b"Hello\x01\x99World")
