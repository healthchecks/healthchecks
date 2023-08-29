from __future__ import annotations

from datetime import timedelta as td
from uuid import UUID

from django.utils.timezone import now

from hc.api.models import Channel, Check
from hc.test import BaseTestCase, TestHttpResponse


class GetCheckTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.now = now().replace(microsecond=0)

        self.a1 = Check(project=self.project)
        self.a1.name = "Alice 1"
        self.a1.slug = "alice-1-custom-slug"
        self.a1.timeout = td(seconds=3600)
        self.a1.grace = td(seconds=900)
        self.a1.n_pings = 0
        self.a1.status = "new"
        self.a1.tags = "a1-tag a1-additional-tag"
        self.a1.desc = "This is description"
        self.a1.filter_subject = True
        self.a1.start_kw = "START"
        self.a1.success_kw = "SUCCESS"
        self.a1.failure_kw = "ERROR"
        self.a1.save()

        self.c1 = Channel.objects.create(project=self.project)
        self.a1.channel_set.add(self.c1)

    def get(
        self, code: UUID | str, api_key: str = "X" * 32, v: int = 1
    ) -> TestHttpResponse:
        url = f"/api/v{v}/checks/{code}"
        return self.client.get(url, HTTP_X_API_KEY=api_key)

    def test_it_works(self) -> None:
        r = self.get(self.a1.code)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertEqual(len(doc), 25)

        self.assertEqual(doc["slug"], "alice-1-custom-slug")
        self.assertEqual(doc["timeout"], 3600)
        self.assertEqual(doc["grace"], 900)
        self.assertEqual(doc["ping_url"], self.a1.url())
        self.assertEqual(doc["last_ping"], None)
        self.assertEqual(doc["n_pings"], 0)
        self.assertEqual(doc["status"], "new")
        self.assertFalse(doc["started"])
        self.assertEqual(doc["channels"], str(self.c1.code))
        self.assertEqual(doc["desc"], "This is description")
        self.assertFalse(doc["manual_resume"])
        self.assertEqual(doc["methods"], "")
        self.assertEqual(doc["subject"], "SUCCESS")
        self.assertEqual(doc["subject_fail"], "ERROR")
        self.assertEqual(doc["start_kw"], "START")
        self.assertEqual(doc["success_kw"], "SUCCESS")
        self.assertEqual(doc["failure_kw"], "ERROR")
        self.assertTrue(doc["filter_subject"])
        self.assertFalse(doc["filter_body"])

    def test_it_handles_invalid_uuid(self) -> None:
        r = self.get("not-an-uuid")
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_check(self) -> None:
        made_up_code = "07c2f548-9850-4b27-af5d-6c9dc157ec02"
        r = self.get(made_up_code)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_unique_key(self) -> None:
        r = self.get(self.a1.unique_key)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        doc = r.json()
        self.assertEqual(len(doc), 25)

        self.assertEqual(doc["timeout"], 3600)
        self.assertEqual(doc["grace"], 900)
        self.assertEqual(doc["ping_url"], self.a1.url())
        self.assertEqual(doc["last_ping"], None)
        self.assertEqual(doc["n_pings"], 0)
        self.assertEqual(doc["status"], "new")
        self.assertEqual(doc["channels"], str(self.c1.code))
        self.assertEqual(doc["desc"], "This is description")

    def test_it_rejects_post_unique_key(self) -> None:
        r = self.csrf_client.post(f"/api/v1/checks/{self.a1.unique_key}")
        self.assertEqual(r.status_code, 405)

    def test_readonly_key_works(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.get(self.a1.code, api_key=self.project.api_key_readonly)
        self.assertEqual(r.status_code, 200)

        # When using readonly keys, the ping URLs should not be exposed:
        for key in ("ping_url", "update_url", "pause_url", "resume_url"):
            self.assertNotContains(r, key)

    def test_v1_reports_status_started(self) -> None:
        self.a1.last_start = now()
        self.a1.save()

        r = self.get(self.a1.code)
        self.assertEqual(r.status_code, 200)

        doc = r.json()
        self.assertEqual(doc["status"], "started")
        self.assertTrue(doc["started"])

    def test_v2_reports_started_separately(self) -> None:
        self.a1.last_start = now()
        self.a1.save()

        r = self.get(self.a1.code, v=2)
        self.assertEqual(r.status_code, 200)

        doc = r.json()
        self.assertEqual(doc["status"], "new")
        self.assertTrue(doc["started"])

    def test_v1_by_unique_key_reports_status_started(self) -> None:
        self.a1.last_start = now()
        self.a1.save()

        r = self.get(self.a1.unique_key)
        doc = r.json()
        self.assertEqual(doc["status"], "started")
        self.assertTrue(doc["started"])

    def test_v2_by_unique_key_reports_started_separately(self) -> None:
        self.a1.last_start = now()
        self.a1.save()

        r = self.get(self.a1.unique_key, v=2)
        doc = r.json()
        self.assertEqual(doc["status"], "new")
        self.assertTrue(doc["started"])
