from __future__ import annotations

from datetime import timedelta as td

from hc.api.models import Check
from hc.test import BaseTestCase, TestHttpResponse


class GetBadgesTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.a1 = Check(project=self.project, name="Alice 1")
        self.a1.timeout = td(seconds=3600)
        self.a1.grace = td(seconds=900)
        self.a1.n_pings = 0
        self.a1.status = "new"
        self.a1.tags = "foo bar"
        self.a1.save()

        self.url = "/api/v1/badges/"

    def get(self, api_key: str = "X" * 32, qs: str = "") -> TestHttpResponse:
        return self.client.get(self.url + qs, HTTP_X_API_KEY=api_key)

    def test_it_works(self) -> None:
        r = self.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertTrue("foo" in doc["badges"])
        self.assertTrue("svg" in doc["badges"]["foo"])

    def test_readonly_key_is_allowed(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.get(api_key=self.project.api_key_readonly)
        self.assertEqual(r.status_code, 200)

    def test_it_rejects_post(self) -> None:
        r = self.csrf_client.post(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 405)

    def test_it_handles_missing_api_key(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(r, "missing api key", status_code=401)
