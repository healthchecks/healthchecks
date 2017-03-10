from hc.test import BaseTestCase


class CronPreviewTestCase(BaseTestCase):

    def test_it_works(self):
        payload = {
            "schedule": "* * * * *",
            "tz": "UTC"
        }
        r = self.client.post("/checks/cron_preview/", payload)
        self.assertContains(r, "cron-preview-title", status_code=200)

    def test_it_handles_invalid_cron_expression(self):
        for schedule in [None, "", "*", "100 100 100 100 100"]:
            payload = {"schedule": schedule, "tz": "UTC"}
            r = self.client.post("/checks/cron_preview/", payload)
            self.assertContains(r, "Invalid cron expression", status_code=200)

    def test_it_handles_invalid_timezone(self):
        for tz in [None, "", "not-a-timezone"]:
            payload = {"schedule": "* * * * *", "tz": tz}
            r = self.client.post("/checks/cron_preview/", payload)
            self.assertContains(r, "Invalid timezone", status_code=200)

    def test_it_handles_missing_arguments(self):
        r = self.client.post("/checks/cron_preview/", {})
        self.assertContains(r, "Invalid cron expression", status_code=200)

    def test_it_rejects_get(self):
        r = self.client.get("/checks/cron_preview/", {})
        self.assertEqual(r.status_code, 405)
