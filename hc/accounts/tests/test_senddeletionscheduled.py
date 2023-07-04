from __future__ import annotations

import re
from datetime import timedelta as td
from unittest.mock import Mock

from django.core import mail
from django.utils.timezone import now

from hc.accounts.management.commands.senddeletionscheduled import Command
from hc.test import BaseTestCase


def counts(result):
    """Extract integer values from command's return value."""
    return [int(s) for s in re.findall(r"\d+", result)]


class SendDeletionNoticesTestCase(BaseTestCase):
    def test_it_skips_profiles_with_deletion_scheduled_date_not_set(self):
        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        result = cmd.handle()
        self.assertEqual(counts(result), [0])
        self.assertEqual(len(mail.outbox), 0)

    def test_it_sends_notice(self):
        self.profile.deletion_scheduled_date = now() + td(days=31)
        self.profile.save()

        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        result = cmd.handle()
        self.assertEqual(counts(result), [1])

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Account Deletion Warning")

    def test_it_skips_profiles_with_deletion_scheduled_date_in_past(self):
        self.profile.deletion_scheduled_date = now() - td(minutes=1)
        self.profile.save()

        cmd = Command(stdout=Mock())
        cmd.pause = Mock()  # don't pause for 1s

        result = cmd.handle()
        self.assertEqual(counts(result), [0])
        self.assertEqual(len(mail.outbox), 0)
