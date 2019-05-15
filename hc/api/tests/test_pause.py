from datetime import timedelta as td

from django.utils.timezone import now
from hc.api.models import Check
from hc.test import BaseTestCase


class PauseTestCase(BaseTestCase):
    def test_it_works(self):
        check = Check.objects.create(project=self.project, status="up")

        url = "/api/v1/checks/%s/pause" % check.code
        r = self.client.post(
            url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        check.refresh_from_db()
        self.assertEqual(check.status, "paused")

    def test_it_handles_options(self):
        check = Check.objects.create(project=self.project, status="up")

        r = self.client.options("/api/v1/checks/%s/pause" % check.code)
        self.assertEqual(r.status_code, 204)
        self.assertIn("POST", r["Access-Control-Allow-Methods"])

    def test_it_only_allows_post(self):
        url = "/api/v1/checks/1659718b-21ad-4ed1-8740-43afc6c41524/pause"

        r = self.client.get(url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 405)

    def test_it_validates_ownership(self):
        check = Check.objects.create(project=self.bobs_project, status="up")

        url = "/api/v1/checks/%s/pause" % check.code
        r = self.client.post(
            url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )

        self.assertEqual(r.status_code, 403)

    def test_it_validates_uuid(self):
        url = "/api/v1/checks/not-uuid/pause"
        r = self.client.post(
            url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )

        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_check(self):
        url = "/api/v1/checks/07c2f548-9850-4b27-af5d-6c9dc157ec02/pause"
        r = self.client.post(
            url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )

        self.assertEqual(r.status_code, 404)

    def test_it_clears_last_start_alert_after(self):
        check = Check(project=self.project, status="up")
        check.last_start = now()
        check.alert_after = check.last_start + td(hours=1)
        check.save()

        url = "/api/v1/checks/%s/pause" % check.code
        r = self.client.post(
            url, "", content_type="application/json", HTTP_X_API_KEY="X" * 32
        )

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        check.refresh_from_db()
        self.assertEqual(check.last_start, None)
        self.assertEqual(check.alert_after, None)
