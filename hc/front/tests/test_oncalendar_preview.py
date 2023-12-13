from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from hc.test import BaseTestCase

CURRENT_TIME = datetime(2020, 1, 1, tzinfo=timezone.utc)
MOCK_NOW = Mock(return_value=CURRENT_TIME)


@patch("hc.front.views.now", MOCK_NOW)
class OnCalendarPreviewTestCase(BaseTestCase):
    url = "/checks/oncalendar_preview/"

    def test_it_works(self) -> None:
        payload = {"schedule": "*:*", "tz": "UTC"}
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "oncalendar-preview-title", status_code=200)
        self.assertContains(r, "2020-01-01 00:01:00 UTC")

    def test_it_handles_single_result(self) -> None:
        payload = {"schedule": "2020-02-01", "tz": "UTC"}
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "oncalendar-preview-title", status_code=200)
        self.assertContains(r, "2020-02-01 00:00:00 UTC")
