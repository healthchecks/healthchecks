from __future__ import annotations

from urllib.parse import urlencode

from hc.test import BaseTestCase


class ValidateScheduleTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = "/checks/validate_schedule/"

    def _url(self, schedule: str, kind: str) -> str:
        params = {"schedule": schedule, "kind": kind}
        return "/checks/validate_schedule/?" + urlencode(params)

    def test_it_validates_cron_schedule(self) -> None:
        r = self.client.get(self._url("* * * * *", "cron"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["result"])

    def test_it_validates_oncalendar_schedule(self) -> None:
        r = self.client.get(self._url("12:34", "oncalendar"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["result"])

    def test_it_rejects_bad_schedules(self) -> None:
        # Bad cron schedules
        for v in ["a", "* * * *", "1-1000 * * * *", "0 0 */100 * MON#2"]:
            r = self.client.get(self._url(v, "cron"))
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.json()["result"])
        # Bad oncalendar schedules
        for v in ["12:345"]:
            r = self.client.get(self._url(v, "oncalendar"))
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.json()["result"])
