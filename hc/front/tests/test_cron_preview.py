from datetime import datetime

from hc.test import BaseTestCase
from mock import patch
import pytz


class CronPreviewTestCase(BaseTestCase):
    def test_it_works(self):
        payload = {"schedule": "* * * * *", "tz": "UTC"}
        r = self.client.post("/checks/cron_preview/", payload)
        self.assertContains(r, "cron-preview-title", status_code=200)

    def test_it_rejects_invalid_cron_expression(self):
        samples = ["", "*", "100 100 100 100 100", "* * * * * *", "1,2 3,* * * *"]

        for schedule in samples:
            payload = {"schedule": schedule, "tz": "UTC"}
            r = self.client.post("/checks/cron_preview/", payload)
            self.assertContains(r, "Invalid cron expression", status_code=200)

    def test_it_handles_invalid_timezone(self):
        for tz in ["", "not-a-timezone"]:
            payload = {"schedule": "* * * * *", "tz": tz}
            r = self.client.post("/checks/cron_preview/", payload)
            self.assertContains(r, "Invalid timezone", status_code=200)

    def test_it_handles_missing_arguments(self):
        r = self.client.post("/checks/cron_preview/", {})
        self.assertContains(r, "Invalid timezone", status_code=200)

    def test_it_rejects_get(self):
        r = self.client.get("/checks/cron_preview/", {})
        self.assertEqual(r.status_code, 405)

    @patch("hc.front.views.timezone.now")
    def test_it_handles_dst_transition(self, mock_now):
        # Consider year 2018, Riga, Latvia:
        # The daylight-saving-time ends at 4AM on October 28.
        # At that time, the clock is turned back one hour.
        # So, on that date,  3AM happens *twice* and saying
        # "3AM on October 28" is ambiguous.
        mock_now.return_value = datetime(2018, 10, 26, tzinfo=pytz.UTC)

        # This schedule will hit the ambiguous date. Cron preview must
        # be able to handle this:
        payload = {"schedule": "0 3 * * *", "tz": "Europe/Riga"}
        r = self.client.post("/checks/cron_preview/", payload)
        self.assertNotContains(r, "Invalid cron expression", status_code=200)
