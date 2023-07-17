from __future__ import annotations

import re
from datetime import timedelta as td
from unittest.mock import Mock

from django.core import mail
from django.utils.timezone import now

from hc.accounts.management.commands.senddeletionscheduled import Command
from hc.accounts.models import Member, Project
from hc.api.models import Check
from hc.test import BaseTestCase


def counts(result):
    """Extract integer values from command's return value."""
    return [int(s) for s in re.findall(r"\d+", result)]


class SendDeletionScheduledTestCase(BaseTestCase):
    def test_it_sends_notice(self):
        self.profile.deletion_scheduled_date = now() + td(days=31)
        self.profile.save()

        Check.objects.create(project=self.project)
        Check.objects.create(project=self.project)

        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        result = cmd.handle()
        self.assertEqual(counts(result), [1])

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Account Deletion Warning")
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertIn("Owner: alice@example.org", email.body)
        self.assertIn("Number of checks in the account: 2", email.body)

    def test_it_sends_notice_to_team_members(self):
        self.profile.deletion_scheduled_date = now() + td(days=31)
        self.profile.save()

        self.bob.last_login = now()
        self.bob.save()

        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        result = cmd.handle()
        self.assertEqual(counts(result), [1])

        self.assertEqual(mail.outbox[0].to, ["alice@example.org", "bob@example.org"])

    def test_it_skips_profiles_with_deletion_scheduled_date_not_set(self):
        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        result = cmd.handle()
        self.assertEqual(counts(result), [0])
        self.assertEqual(len(mail.outbox), 0)

    def test_it_skips_profiles_with_deletion_scheduled_date_in_past(self):
        self.profile.deletion_scheduled_date = now() - td(minutes=1)
        self.profile.save()

        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        result = cmd.handle()
        self.assertEqual(counts(result), [0])
        self.assertEqual(len(mail.outbox), 0)

    def test_it_avoids_duplicate_recipients(self):
        self.profile.deletion_scheduled_date = now() + td(days=31)
        self.profile.save()

        self.bob.last_login = now()
        self.bob.save()

        second_project = Project.objects.create(owner=self.alice)
        Member.objects.create(
            user=self.bob, project=second_project, role=Member.Role.REGULAR
        )

        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        cmd.handle()
        # Bob should be listed as a recipient a single time, despite two memberships:
        self.assertEqual(mail.outbox[0].to, ["alice@example.org", "bob@example.org"])
