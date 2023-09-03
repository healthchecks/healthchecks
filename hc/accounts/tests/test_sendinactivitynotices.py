from __future__ import annotations

import re
from datetime import timedelta as td
from unittest.mock import Mock, patch

from django.core import mail
from django.utils.timezone import now

from hc.accounts.management.commands.sendinactivitynotices import Command
from hc.accounts.models import Member
from hc.api.models import Check, Ping
from hc.payments.models import Subscription
from hc.test import BaseTestCase

MOCK_SLEEP = Mock()


def counts(result: str) -> list[int]:
    """Extract integer values from command's return value."""
    return [int(s) for s in re.findall(r"\d+", result)]


@patch("hc.accounts.management.commands.sendinactivitynotices.time.sleep", MOCK_SLEEP)
class SendInactivityNoticesTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        # Make alice eligible for notice -- signed up more than 1 year ago
        self.alice.date_joined = now() - td(days=500)
        self.alice.save()

        self.profile.sms_limit = 5
        self.profile.save()

        # remove members from alice's project
        self.project.member_set.all().delete()

    def test_it_sends_notice(self) -> None:
        cmd = Command(stdout=Mock())
        result = cmd.handle()
        self.assertEqual(counts(result), [1, 0, 0])

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.deletion_notice_date)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Inactive Account Notification")

    def test_it_checks_last_login(self) -> None:
        # alice has logged in recently:
        self.alice.last_login = now() - td(days=15)
        self.alice.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_date_joined(self) -> None:
        # alice signed up recently:
        self.alice.date_joined = now() - td(days=15)
        self.alice.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_deletion_notice_date(self) -> None:
        # alice has already received a deletion notice
        self.profile.deletion_notice_date = now() - td(days=15)
        self.profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])

    def test_it_checks_subscription(self) -> None:
        # alice has a subscription
        Subscription.objects.create(user=self.alice, subscription_id="abc123")

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_recently_active_team_members(self) -> None:
        # bob has access to alice's project
        Member.objects.create(user=self.bob, project=self.project)
        self.bobs_profile.last_active_date = now()
        self.bobs_profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 1, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_recently_logged_in_team_members(self) -> None:
        # bob has access to alice's project
        Member.objects.create(user=self.bob, project=self.project)
        self.bob.last_login = now()
        self.bob.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 1, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_recently_signed_up_team_members(self) -> None:
        # bob has access to alice's project
        Member.objects.create(user=self.bob, project=self.project)

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 1, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_ignores_inactive_team_members(self) -> None:
        # bob has access to alice's project, but is inactive
        Member.objects.create(user=self.bob, project=self.project)
        self.bob.date_joined = now() - td(days=366)
        self.bob.save()

        cmd = Command(stdout=Mock())
        result = cmd.handle()
        # both alice and bob are eligible for deletion
        self.assertEqual(counts(result), [2, 0, 0])

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.deletion_notice_date)

        self.bobs_profile.refresh_from_db()
        self.assertTrue(self.bobs_profile.deletion_notice_date)

    def test_it_checks_recent_pings(self) -> None:
        check = Check.objects.create(project=self.project)
        Ping.objects.create(owner=check)

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 1])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_last_active_date(self) -> None:
        # alice has been browsing the site recently
        self.profile.last_active_date = now() - td(days=15)
        self.profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])
