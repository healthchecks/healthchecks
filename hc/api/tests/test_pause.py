from hc.api.models import Check
from hc.test import BaseTestCase


class PauseTestCase(BaseTestCase):

    def test_it_works(self):
        check = Check(user=self.alice, status="up")
        check.save()

        url = "/api/v1/checks/%s/pause" % check.code
        r = self.client.post(url, "", content_type="application/json",
                             HTTP_X_API_KEY="abc")

        self.assertEqual(r.status_code, 200)

        check.refresh_from_db()
        self.assertEqual(check.status, "paused")

    def test_it_only_allows_post(self):
        url = "/api/v1/checks/1659718b-21ad-4ed1-8740-43afc6c41524/pause"

        r = self.client.get(url, HTTP_X_API_KEY="abc")
        self.assertEqual(r.status_code, 405)

    def test_it_validates_ownership(self):
        check = Check(user=self.bob, status="up")
        check.save()

        url = "/api/v1/checks/%s/pause" % check.code
        r = self.client.post(url, "", content_type="application/json",
                             HTTP_X_API_KEY="abc")

        self.assertEqual(r.status_code, 403)

    def test_it_validates_uuid(self):
        url = "/api/v1/checks/not-uuid/pause"
        r = self.client.post(url, "", content_type="application/json",
                             HTTP_X_API_KEY="abc")

        self.assertEqual(r.status_code, 400)

    def test_it_handles_missing_check(self):
        url = "/api/v1/checks/07c2f548-9850-4b27-af5d-6c9dc157ec02/pause"
        r = self.client.post(url, "", content_type="application/json",
                             HTTP_X_API_KEY="abc")

        self.assertEqual(r.status_code, 404)
