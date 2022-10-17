from __future__ import annotations

import re
from datetime import timedelta as td
from unittest.mock import Mock

from django.core import mail
from django.utils.timezone import now

from hc.accounts.management.commands.senddeletionnotices import Command
from hc.accounts.models import Member
from hc.api.models import Check, Ping
from hc.test import BaseTestCase


def counts(result):
    """Extract integer values from command's return value."""
    return [int(s) for s in re.findall(r"\d+", result)]


class SendDeletionNoticesTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        # Make alice eligible for notice -- signed up more than 1 year ago
        self.alice.date_joined = now() - td(days=500)
        self.alice.save()

        self.profile.sms_limit = 5
        self.profile.save()

        # remove members from alice's project
        self.project.member_set.all().delete()

    def test_it_sends_notice(self):
        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        result = cmd.handle()
        self.assertEqual(counts(result), [1, 0, 0])

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.deletion_notice_date)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Inactive Account Notification")

    def test_it_checks_last_login(self):
        # alice has logged in recently:
        self.alice.last_login = now() - td(days=15)
        self.alice.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_date_joined(self):
        # alice signed up recently:
        self.alice.date_joined = now() - td(days=15)
        self.alice.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_deletion_notice_date(self):
        # alice has already received a deletion notice
        self.profile.deletion_notice_date = now() - td(days=15)
        self.profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])

    def test_it_checks_sms_limit(self):
        # alice has a paid account
        self.profile.sms_limit = 50
        self.profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_team_members(self):
        # bob has access to alice's project
        Member.objects.create(user=self.bob, project=self.project)

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 1, 0])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_recent_pings(self):
        check = Check.objects.create(project=self.project)
        Ping.objects.create(owner=check)

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 1])

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_last_active_date(self):
        # alice has been browsing the site recently
        self.profile.last_active_date = now() - td(days=15)
        self.profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(counts(result), [0, 0, 0])
