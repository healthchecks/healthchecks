from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from hc.test import BaseTestCase


class CronPreviewTestCase(BaseTestCase):
    url = "/checks/cron_preview/"

    def test_it_works(self) -> None:
        payload = {"schedule": "* * * * *", "tz": "UTC"}
        r = self.client.post(self.url, payload)
        self.assertContains(r, "cron-preview-title", status_code=200)
        self.assertContains(r, "“Every minute”")

    def test_it_accepts_sunday_7(self) -> None:
        payload = {"schedule": "* * * * 7", "tz": "UTC"}
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Expected Ping Dates", status_code=200)
        self.assertNotContains(r, "Invalid cron expression", status_code=200)

    def test_it_rejects_invalid_cron_expression(self) -> None:
        samples = ["", "*", "100 100 100 100 100", "* * * * * *"]

        for schedule in samples:
            payload = {"schedule": schedule, "tz": "UTC"}
            r = self.client.post(self.url, payload)
            self.assertContains(r, "Invalid cron expression", status_code=200)

    def test_it_handles_invalid_timezone(self) -> None:
        for tz in ["", "not-a-timezone"]:
            payload = {"schedule": "* * * * *", "tz": tz}
            r = self.client.post(self.url, payload)
            self.assertContains(r, "Invalid timezone", status_code=200)

    def test_it_handles_missing_arguments(self) -> None:
        r = self.client.post(self.url, {})
        self.assertContains(r, "Invalid timezone", status_code=200)

    def test_it_rejects_get(self) -> None:
        r = self.client.get(self.url, {})
        self.assertEqual(r.status_code, 405)

    @patch("hc.front.views.now")
    def test_it_handles_dst_transition(self, mock_now: Mock) -> None:
        # Consider year 2018, Riga, Latvia:
        # The daylight-saving-time ends at 4AM on October 28.
        # At that time, the clock is turned back one hour.
        # So, on that date,  3AM happens *twice* and saying
        # "3AM on October 28" is ambiguous.
        mock_now.return_value = datetime(2018, 10, 26, tzinfo=timezone.utc)

        # This schedule will hit the ambiguous date. Cron preview must
        # be able to handle this:
        payload = {"schedule": "0 3 * * *", "tz": "Europe/Riga"}
        r = self.client.post(self.url, payload)
        self.assertNotContains(r, "Invalid cron expression", status_code=200)

    def test_it_handles_feb_29(self) -> None:
        payload = {"schedule": "0 0 29 2 *", "tz": "UTC"}
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Feb 29")

    def test_it_handles_no_matches(self) -> None:
        payload = {"schedule": "0 0 */100 * MON#2", "tz": "UTC"}
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid cron expression", status_code=200)
