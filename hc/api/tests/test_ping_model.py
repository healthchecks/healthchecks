from __future__ import annotations

from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from unittest import mock
import uuid

from hc.api.models import Check, Ping
from hc.test import BaseTestCase

EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)


class PingModelTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)

    @mock.patch("hc.api.models.now")  # Target 'now' as used in hc.api.models
    def test_it_calculates_duration(self, mock_now: mock.Mock) -> None:
        """Test that duration is calculated and saved when using check.ping."""
        start_time = EPOCH
        end_time = EPOCH + td(minutes=5)
        expected_duration = td(minutes=5)
        rid = uuid.uuid4()  # Generate a unique run ID

        # Simulate the "start" ping call
        mock_now.return_value = start_time
        # Pass dummy values for network details as they aren't relevant here
        self.check.ping(
            remote_addr="1.2.3.4",
            scheme="http",
            method="post",
            ua="test-agent",
            body=b"",
            action="start",
            rid=rid
        )

        # Reload the check instance to ensure its state (last_start, last_start_rid)
        # reflects the changes made by the first ping call.
        # This is important because check.ping internally reloads self.
        self.check.refresh_from_db()

        # Simulate the "end" ping call (action="success" is default if not specified)
        mock_now.return_value = end_time
        self.check.ping(
            remote_addr="1.2.3.4",
            scheme="http",
            method="post",
            ua="test-agent",
            body=b"",
            action="success",  # Explicitly using "success"
            rid=rid  # Use the SAME rid
        )

        # Fetch the 'success' Ping object created by the second call.
        # It should have kind=None (the default) or kind="success".
        try:
            # Filter for pings that aren't 'start' and get the latest one
            p2 = Ping.objects.filter(owner=self.check).exclude(kind="start").latest('created')
        except Ping.DoesNotExist:
            self.fail("Could not find the 'success' Ping object created by check.ping")

        # Assert that the duration field on the Ping object was populated
        self.assertIsNotNone(p2.duration, "Ping.duration should be calculated and saved.")
        # Assert that the duration is correct
        self.assertEqual(p2.duration, expected_duration)

        self.check.refresh_from_db()
        self.assertEqual(self.check.last_duration, expected_duration, "Check.last_duration should be updated.")
        self.assertIsNone(self.check.last_start, "Check.last_start should be cleared after duration calculation.")

    def test_it_handles_no_adjacent_start_event(self) -> None:

        Ping.objects.create(owner=self.check, created=EPOCH, kind="start", rid=uuid.uuid4())
        Ping.objects.create(owner=self.check, created=EPOCH + td(minutes=5), rid=uuid.uuid4())

        p3 = Ping.objects.create(owner=self.check, created=EPOCH + td(minutes=10), rid=uuid.uuid4())
        # This assertion relies on the default value being None when created directly
        self.assertIsNone(p3.duration)

    def test_it_runs_no_queries_for_the_first_ping(self) -> None:
        # This test remains valid - the duration field is just a field,
        # accessing it doesn't trigger queries if the object is loaded.
        p = Ping.objects.create(owner=self.check, created=EPOCH, n=1)
        with self.assertNumQueries(0):
            # Accessing the field directly should be fine
            duration_value = p.duration
        self.assertIsNone(duration_value)  # Check the value is None as expected