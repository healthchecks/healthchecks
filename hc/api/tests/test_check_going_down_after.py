from __future__ import annotations

from datetime import timedelta as td

from django.test import TestCase
from django.utils.timezone import now

from hc.api.models import Check


class CheckModelTestCase(TestCase):
    def test_it_handles_new_check(self) -> None:
        check = Check()
        self.assertEqual(check.going_down_after(), None)

    def test_it_handles_paused_check(self) -> None:
        check = Check(status="paused")
        check.last_ping = now() - td(days=2)
        self.assertEqual(check.going_down_after(), None)

    def test_it_handles_up(self) -> None:
        check = Check(status="up")
        check.last_ping = now() - td(hours=1)
        expected_aa = check.last_ping + td(days=1, hours=1)
        self.assertEqual(check.going_down_after(), expected_aa)

    def test_it_handles_paused_then_started_check(self) -> None:
        check = Check(status="paused")
        check.last_start = now() - td(days=2)

        expected_aa = check.last_start + td(hours=1)
        self.assertEqual(check.going_down_after(), expected_aa)

    def test_it_handles_down(self) -> None:
        check = Check(status="down")
        check.last_ping = now() - td(hours=1)
        self.assertEqual(check.going_down_after(), None)

    def test_it_handles_down_then_started_check(self) -> None:
        check = Check(status="down")
        check.last_start = now() - td(minutes=10)

        self.assertEqual(check.going_down_after(), None)
