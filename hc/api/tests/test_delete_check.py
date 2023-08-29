from __future__ import annotations

from django.utils.timezone import now

from hc.api.models import Check
from hc.test import BaseTestCase


class DeleteCheckTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/api/v2/checks/{self.check.code}"
        self.urlv1 = f"/api/v1/checks/{self.check.code}"

    def test_it_works(self) -> None:
        r = self.client.delete(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        # It should be gone--
        self.assertFalse(Check.objects.filter(code=self.check.code).exists())

    def test_it_handles_missing_check(self) -> None:
        self.check.delete()
        r = self.client.delete(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_options(self) -> None:
        r = self.client.options(self.url)
        self.assertEqual(r.status_code, 204)
        self.assertIn("DELETE", r["Access-Control-Allow-Methods"])

    def test_it_handles_missing_api_key(self) -> None:
        r = self.client.delete(self.url)
        self.assertContains(r, "missing api key", status_code=401)

    def test_v1_reports_status_started(self) -> None:
        self.check.last_start = now()
        self.check.save()

        r = self.client.delete(self.urlv1, HTTP_X_API_KEY="X" * 32)
        doc = r.json()
        self.assertEqual(doc["status"], "started")
        self.assertTrue(doc["started"])

    def test_v2_reports_started_separately(self) -> None:
        self.check.last_start = now()
        self.check.save()

        r = self.client.delete(self.url, HTTP_X_API_KEY="X" * 32)
        doc = r.json()
        self.assertEqual(doc["status"], "new")
        self.assertTrue(doc["started"])
