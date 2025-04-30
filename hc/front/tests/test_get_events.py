from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from uuid import uuid4
import uuid
from unittest import mock

from hc.api.models import Check, Ping
from hc.front.views import _get_events
from hc.test import BaseTestCase

EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)


class GetEventsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, created=EPOCH)
        self.start = self.check.created
        self.end = EPOCH + td(days=10)

    def test_it_calculates_duration(self) -> None:
        Ping.objects.create(owner=self.check, n=1, created=EPOCH, kind="start")
        Ping.objects.create(owner=self.check, n=2, created=EPOCH + td(minutes=5))

        with self.assertNumQueries(2):
            pings = _get_events(self.check, 100, start=self.start, end=self.end)
        with self.assertNumQueries(0):
            assert isinstance(pings[0], Ping)
            self.assertEqual(pings[0].duration, td(minutes=5))

    @mock.patch("hc.api.models.now")  # Patch 'now' where Check.ping uses it
    def test_it_delegates_duration_calculation_to_model(self, mock_now: mock.Mock) -> None:
        """
        Checks that if _get_events cannot dynamically calculate duration (because
        it only fetches the 'end' ping due to limit=1), it correctly reflects
        the duration previously calculated and saved by Check.ping.
        """
        start_time = EPOCH
        end_time = EPOCH + td(minutes=5)
        expected_duration = td(minutes=5)
        rid = uuid.uuid4()
        mock_now.return_value = start_time
        self.check.ping(
            remote_addr="1.2.3.4",
            scheme="http",
            method="post",
            ua="test-agent",
            body=b"",
            action="start",
            rid=rid
        )
        # Reload check state after the first ping
        self.check.refresh_from_db()

        # 2. Simulate the "end" ping (this should calculate and save duration)
        mock_now.return_value = end_time
        self.check.ping(
            remote_addr="1.2.3.4",
            scheme="http",
            method="post",
            ua="test-agent",
            body=b"",
            action="success",  # 'success' is also the default if action isn't 'start'/'fail'/etc.
            rid=rid  # Use the same rid
        )
        with self.assertNumQueries(2):
            pings = _get_events(self.check, 1, start=self.start, end=self.end)

        with self.assertNumQueries(0):
            self.assertEqual(len(pings), 1, "Should have fetched exactly one event")
            # Ensure we got the Ping object as expected
            ping_event = pings[0]
            self.assertIsInstance(ping_event, Ping, "Fetched event should be a Ping object")
            self.assertNotEqual(ping_event.kind, "start", "Fetched event should not be the 'start' ping")

            # Core Assertion: Verify the duration field saved by check.ping
            self.assertIsNotNone(
                ping_event.duration,
                "Ping.duration should have been calculated and saved by check.ping"
            )
            self.assertEqual(
                ping_event.duration,
                expected_duration,
                "The fetched ping's duration field should match the expected value"
            )

    def test_it_calculates_overlapping_durations(self) -> None:
        m = td(minutes=1)
        a, b = uuid4(), uuid4()
        self.check.ping_set.create(n=1, rid=a, created=EPOCH, kind="start")
        self.check.ping_set.create(n=2, rid=b, created=EPOCH + m, kind="start")
        self.check.ping_set.create(n=3, rid=a, created=EPOCH + m * 2)
        self.check.ping_set.create(n=4, rid=b, created=EPOCH + m * 6)

        with self.assertNumQueries(2):
            pings = _get_events(self.check, 100, start=self.start, end=self.end)

        with self.assertNumQueries(0):
            assert isinstance(pings[0], Ping)
            self.assertEqual(pings[0].duration, td(minutes=5))
            assert isinstance(pings[1], Ping)
            self.assertEqual(pings[1].duration, td(minutes=2))

    def test_it_disables_duration_display(self) -> None:
        # Set up a worst case scenario where each success ping has an unique rid,
        # and there are no "start" pings:
        for i in range(1, 12):
            self.check.ping_set.create(n=i, rid=uuid4(), created=EPOCH + td(minutes=i))

        # Make sure we don't run Ping.duration() per ping:
        with self.assertNumQueries(2):
            pings = _get_events(self.check, 100, start=self.start, end=self.end)

        with self.assertNumQueries(0):
            for ping in pings:
                assert isinstance(ping, Ping)
                self.assertIsNone(ping.duration)
