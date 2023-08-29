from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td
from datetime import timezone

from hc.api.models import Check, Ping
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
