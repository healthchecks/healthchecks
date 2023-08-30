from __future__ import annotations

from datetime import timedelta as td
from unittest import TestCase

from hc.front.templatetags.hc_extras import hc_duration


class HcExtrasTestCase(TestCase):
    def test_hc_duration_works(self) -> None:
        samples = [
            (60, "1 minute"),
            (120, "2 minutes"),
            (3600, "1 hour"),
            (3660, "1 hour 1 minute"),
            (86400, "1 day"),
            (604800, "1 week"),
            (2419200, "4 weeks"),
            (2592000, "30 days"),
            (3801600, "44 days"),
        ]

        for seconds, expected_result in samples:
            result = hc_duration(td(seconds=seconds))
            self.assertEqual(result, expected_result)
