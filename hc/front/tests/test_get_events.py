from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td

from django.utils import timezone

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
