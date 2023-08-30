from __future__ import annotations

from urllib.parse import urlencode

from hc.test import BaseTestCase


class ValidateScheduleTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = "/checks/validate_schedule/"

    def _url(self, schedule: str) -> str:
        return "/checks/validate_schedule/?" + urlencode({"schedule": schedule})

    def test_it_works(self) -> None:
        r = self.client.get(self._url("* * * * *"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["result"])

    def test_it_rejects_bad_schedules(self) -> None:
        for v in ["a", "* * * *", "1-1000 * * * *", "0 0 */100 * MON#2"]:
            r = self.client.get(self._url(v))
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.json()["result"])
