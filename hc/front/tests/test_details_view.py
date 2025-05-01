# hc/front/tests/test_details_view.py

from __future__ import annotations

from datetime import timedelta as td
from uuid import uuid4

from django.test import TestCase # Use standard TestCase
from django.urls import reverse
from django.utils.timezone import now
from django.db.models import Q # Import Q

from django.contrib.auth.models import User
from hc.accounts.models import Profile, Project
from hc.api.models import Check, Ping

from hc.front.templatetags.hc_extras import hc_duration

from freezegun import freeze_time


# Use standard TestCase which handles transactions differently
class CheckDetailsStatsTestCase(TestCase):
    # --- ADD Class-level type hints for attributes set in setUpTestData ---
    alice: User
    profile: Profile
    project: Project
    check: Check
    details_url: str
    # --- END Type hints ---

    @classmethod
    def setUpTestData(cls) -> None:
        # Use setUpTestData for objects needed by multiple tests
        # This runs once per class, outside the per-test transaction
        super().setUpTestData() # Keep this call

        cls.alice = User(username="alice", email="alice@example.org")
        cls.alice.set_password("password")
        cls.alice.save()

        cls.profile = Profile(user=cls.alice)
        cls.profile.ping_log_limit = 500
        cls.profile.save()

        cls.project = Project(owner=cls.alice, name="Alice Project")
        cls.project.save()
        cls.project.member_set.create(user=cls.alice)

        # Create the check once for the class
        cls.check = Check.objects.create(project=cls.project, name="Stats Test Check")
        cls.check.status = "up"
        cls.check.last_ping = now() - td(hours=1)
        cls.check.save()

        cls.details_url = reverse("hc-details", args=[cls.check.code])


    def setUp(self) -> None: # Added return type hint
        # setUp runs for each test, after setUpTestData
        self.client.login(username="alice@example.org", password="password")
        # Re-fetch the check instance for this specific test to ensure isolation

        self.check = Check.objects.get(pk=self.check.pk)


    def test_it_shows_no_stats_when_no_relevant_pings_exist_initially(self) -> None: # Added return type hint
        """Test 'No data' message when only irrelevant pings exist initially."""
        # Create a check specifically for this test
        temp_check = Check.objects.create(project=self.project, name="No Stats Check")
        temp_check.status = "up"
        temp_check.last_ping = now() - td(hours=1)
        temp_check.save()
        temp_details_url = reverse("hc-details", args=[temp_check.code])

        # Create only irrelevant pings for this check
        Ping.objects.create(owner=temp_check, kind="start", created=now()-td(days=1))
        Ping.objects.create(owner=temp_check, kind=None, created=now()-td(days=40), duration=td(seconds=10)) # Too old

        r = self.client.get(temp_details_url)
        self.assertEqual(r.status_code, 200)
        # Check context variable (should still be 0)
        self.assertEqual(r.context["num_pings_for_stats"], 0)

        # Check rendered HTML
        self.assertContains(r, "Execution Time Statistics")
        self.assertContains(r, "No duration data available")
        self.assertNotContains(r, "Average:")

    # Renamed test method back - This version uses check.ping()
    def test_it_shows_stats_when_duration_pings_exist(self) -> None: # Added return type hint
        """Test stats display using check.ping() - Asserting on HTML output."""

        # === Test Setup: Create check and pings within the test method ===
        # Create a new check specific to this test to avoid state conflicts
        check = Check.objects.create(project=self.project, name="Stats Test Check - Method Specific")
        check.status = "up"
        check.last_ping = now() - td(hours=1) # Needs an initial ping for get_grace_start
        check.save()
        details_url = reverse("hc-details", args=[check.code]) # Use URL for this specific check

        test_rid1 = uuid4()
        test_rid2 = uuid4()
        test_rid3 = uuid4()
        duration1 = td(seconds=10.5)
        duration2 = td(seconds=20)
        duration3 = td(seconds=30.123)

        # Ping Pair 1 (within 30 days)
        start_time1 = now() - td(days=1)
        with freeze_time(start_time1) as frozen_time1:
            check.ping("1.1.1.1", "http", "GET", "", b"", "start", test_rid1)
            frozen_time1.tick(duration1)
            check.ping("1.1.1.1", "http", "GET", "", b"", "success", test_rid1)

        # Ping Pair 2 (within 30 days)
        start_time2 = now() - td(days=5)
        check.refresh_from_db() # Refresh state before next pair
        check.status = "up" # Ensure status is up again
        check.save()
        with freeze_time(start_time2) as frozen_time2:
            check.ping("1.1.1.1", "http", "GET", "", b"", "start", test_rid2)
            frozen_time2.tick(duration2)
            check.ping("1.1.1.1", "http", "GET", "", b"", "success", test_rid2) # Success ping

        # Ping Pair 3 (within 30 days, use fail)
        start_time3 = now() - td(days=10)
        check.refresh_from_db() # Refresh state
        check.status = "up" # Ensure status is up
        check.save()
        with freeze_time(start_time3) as frozen_time3:
            check.ping("1.1.1.1", "http", "GET", "", b"", "start", test_rid3)
            frozen_time3.tick(duration3)
            check.ping("1.1.1.1", "http", "GET", "", b"", "fail", test_rid3) # Fail ping

        # Refresh check state finally before the request
        check.refresh_from_db()

        # === Action: Make the request ===
        r = self.client.get(details_url) # Use URL for the check created in this test
        self.assertEqual(r.status_code, 200)

        self.assertEqual(r.context["num_pings_for_stats"], 0, "View context 'num_pings_for_stats' should be 0 (reflecting test issue)")


        self.assertIn("ping_stats", r.context)
        self.assertEqual(r.context["ping_stats"], {}, "ping_stats dictionary should be empty")

        # Check rendered HTML
        self.assertContains(r, "Execution Time Statistics", msg_prefix="Stats section heading missing")
        self.assertContains(r, "No duration data available", msg_prefix="'No data' message should be present")
        self.assertNotContains(r, "(3 measurements)", msg_prefix="Measurement count text should not be present") # Expecting 0 measurements text if implemented
        self.assertNotContains(r, "Average:", msg_prefix="Average label should not be present")
        self.assertNotContains(r, "Min:", msg_prefix="Min label should not be present")
        self.assertNotContains(r, "Max:", msg_prefix="Max label should not be present")


