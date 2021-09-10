from hc.api.models import Check
from hc.test import BaseTestCase


class DeleteCheckTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/api/v1/checks/{self.check.code}"

    def test_it_works(self):
        r = self.client.delete(self.url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        # It should be gone--
        self.assertFalse(Check.objects.filter(code=self.check.code).exists())

    def test_it_handles_missing_check(self):
        url = "/api/v1/checks/07c2f548-9850-4b27-af5d-6c9dc157ec02"
        r = self.client.delete(url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_options(self):
        r = self.client.options(self.url)
        self.assertEqual(r.status_code, 204)
        self.assertIn("DELETE", r["Access-Control-Allow-Methods"])

    def test_it_handles_missing_api_key(self):
        r = self.client.delete(self.url)
        self.assertContains(r, "missing api key", status_code=401)
