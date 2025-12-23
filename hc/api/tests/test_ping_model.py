from __future__ import annotations

from datetime import datetime, timezone
from datetime import timedelta as td
from unittest.mock import Mock, patch
from uuid import uuid4

from hc.api.models import MAX_DURATION, Check, Ping, prepare_durations
from hc.test import BaseTestCase

EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)


class PingModelTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

    def test_it_calculates_duration(self) -> None:
        Ping.objects.create(owner=self.check, created=EPOCH, kind="start")

        p2 = Ping.objects.create(owner=self.check, created=EPOCH + td(minutes=5))
        assert p2.duration
        self.assertEqual(p2.duration.total_seconds(), 300)

    def test_it_handles_no_adjacent_start_event(self) -> None:
        Ping.objects.create(owner=self.check, created=EPOCH, kind="start")
        Ping.objects.create(owner=self.check, created=EPOCH + td(minutes=5))

        p3 = Ping.objects.create(owner=self.check, created=EPOCH + td(minutes=10))
        self.assertIsNone(p3.duration)

    def test_it_runs_no_queries_for_the_first_ping(self) -> None:
        p = Ping.objects.create(owner=self.check, created=EPOCH, n=1)
        with self.assertNumQueries(0):
            self.assertIsNone(p.duration)


class PrepareDurationsTestCase(BaseTestCase):
    def test_it_works(self) -> None:
        p1 = Ping(id=1, created=EPOCH, kind="start")
        p2 = Ping(id=2, created=EPOCH + td(seconds=1))
        prepare_durations([p2, p1])
        self.assertEqual(p2.duration, td(seconds=1))

    def test_it_matches_start_event_by_rid(self) -> None:
        A = "63832bb7-ddd5-4f2d-bf0a-cac885212963"
        B = "beecf8af-7bff-4cbe-b179-49693c15413b"
        p1 = Ping(id=1, created=EPOCH, kind="start", rid=A)
        p2 = Ping(id=2, created=EPOCH + td(seconds=1), kind="start", rid=B)
        p3 = Ping(id=3, created=EPOCH + td(seconds=2), rid=A)
        prepare_durations([p3, p2, p1])
        self.assertEqual(p3.duration, td(seconds=2))

    def test_it_ignores_ign_event(self) -> None:
        p1 = Ping(id=1, created=EPOCH, kind="start")
        p2 = Ping(id=2, created=EPOCH + td(seconds=1), kind="ign")
        p3 = Ping(id=3, created=EPOCH + td(seconds=2))
        prepare_durations([p3, p2, p1])
        self.assertEqual(p3.duration, td(seconds=2))

    def test_it_handles_consecutive_success_signals(self) -> None:
        p1 = Ping(id=1, created=EPOCH, kind="start")
        p2 = Ping(id=2, created=EPOCH + td(seconds=1))
        p3 = Ping(id=3, created=EPOCH + td(seconds=2))
        prepare_durations([p3, p2, p1])
        self.assertEqual(p2.duration, td(seconds=1))
        self.assertIsNone(p3.duration)

    def test_it_caps_misses(self) -> None:
        l = []
        for i in range(0, 15):
            l.insert(0, Ping(id=i, created=EPOCH + td(seconds=i), rid=uuid4()))

        prepare_durations(l)

        # All pings have unique rid values, and there are no matching start events.
        # prepare_durations should fill all duration fields with None values
        # to avoid many expensive calls to Ping.duration()
        for ping in l:
            self.assertIsNone(ping.duration)

    def test_it_applies_max_duration(self) -> None:
        p1 = Ping(id=1, created=EPOCH, kind="start")
        p2 = Ping(id=2, created=EPOCH + MAX_DURATION + td(seconds=1))
        prepare_durations([p2, p1])
        # The time gap between p1 and p2 exceeds hc.api.models.MAX_DURATION
        # so the duration should be None
        self.assertIsNone(p2.duration)

    @patch("hc.api.models.Ping.duration")
    def test_it_defers_to_duration_property(self, mock_duration: Mock) -> None:
        p1 = Ping(id=1, created=EPOCH)
        prepare_durations([p1])
        self.assertEqual(p1.duration, mock_duration)

    def test_it_checks_max_duration_before_deferring(self) -> None:
        p1 = Ping(id=1, created=EPOCH, kind="ign")
        p2 = Ping(id=2, created=EPOCH + MAX_DURATION + td(seconds=1))
        prepare_durations([p2, p1])
        # p1 and p2 are not related, but since the time gap between
        # p1 and p2 exceeds MAX_DURATION, we know it is not worth looking
        # for start events further in the past
        self.assertIsNone(p2.duration)

    def test_it_requires_pings_in_descending_time_order(self) -> None:
        p1 = Ping(id=1, created=EPOCH, kind="start")
        p2 = Ping(id=2, created=EPOCH + td(seconds=1))
        with self.assertRaises(AssertionError):
            prepare_durations([p1, p2])

    def test_it_handles_empty_list(self) -> None:
        prepare_durations([])
