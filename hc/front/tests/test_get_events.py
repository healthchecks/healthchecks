from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from uuid import uuid4

from hc.api.models import Check, Ping
from hc.front.views import _get_events
from hc.test import BaseTestCase

EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)


class GetEventsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)

    def test_it_calculates_duration(self):
        Ping.objects.create(owner=self.check, n=1, created=EPOCH, kind="start")
        Ping.objects.create(owner=self.check, n=2, created=EPOCH + td(minutes=5))

        with self.assertNumQueries(2):
            pings = _get_events(self.check, 100)
            self.assertEqual(pings[0].duration, td(minutes=5))

    def test_it_delegates_duration_calculation_to_model(self):
        Ping.objects.create(owner=self.check, n=1, created=EPOCH, kind="start")
        Ping.objects.create(owner=self.check, n=2, created=EPOCH + td(minutes=5))

        with self.assertNumQueries(3):
            pings = _get_events(self.check, 1)
            self.assertEqual(pings[0].duration, td(minutes=5))

    def test_it_calculates_overlapping_durations(self):
        m = td(minutes=1)
        a, b = uuid4(), uuid4()
        self.check.ping_set.create(n=1, rid=a, created=EPOCH, kind="start")
        self.check.ping_set.create(n=2, rid=b, created=EPOCH + m, kind="start")
        self.check.ping_set.create(n=3, rid=a, created=EPOCH + m * 2)
        self.check.ping_set.create(n=4, rid=b, created=EPOCH + m * 6)

        with self.assertNumQueries(2):
            pings = _get_events(self.check, 100)
            self.assertEqual(pings[0].duration, td(minutes=5))
            self.assertEqual(pings[1].duration, td(minutes=2))

    def test_it_disables_duration_display(self):
        # Set up a worst case scenario where each success ping has an unique rid,
        # and there are no "start" pings:
        for i in range(1, 12):
            self.check.ping_set.create(n=i, rid=uuid4(), created=EPOCH + td(minutes=i))

        # Make sure we don't run Ping.duration() per ping:
        with self.assertNumQueries(2):
            pings = _get_events(self.check, 100)
            for ping in pings:
                self.assertIsNone(ping.duration)
