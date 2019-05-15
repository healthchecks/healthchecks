from hc.api.models import Check
from hc.test import BaseTestCase


class DeleteCheckTestCase(BaseTestCase):
    def setUp(self):
        super(DeleteCheckTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project)

    def test_it_works(self):
        r = self.client.delete(
            "/api/v1/checks/%s" % self.check.code, HTTP_X_API_KEY="X" * 32
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")

        # It should be gone--
        self.assertFalse(Check.objects.filter(code=self.check.code).exists())

    def test_it_handles_missing_check(self):
        url = "/api/v1/checks/07c2f548-9850-4b27-af5d-6c9dc157ec02"
        r = self.client.delete(url, HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 404)

    def test_it_handles_options(self):
        r = self.client.options("/api/v1/checks/%s" % self.check.code)
        self.assertEqual(r.status_code, 204)
        self.assertIn("DELETE", r["Access-Control-Allow-Methods"])
