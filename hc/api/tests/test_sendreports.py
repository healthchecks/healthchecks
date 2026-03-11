from __future__ import annotations

from datetime import date, datetime, timezone
from datetime import timedelta as td
from unittest.mock import Mock, patch

import time_machine
from django.core import mail
from django.utils.timezone import now

from hc.api.management.commands.sendreports import Command
from hc.api.models import Check, Flip
from hc.test import BaseTestCase

CURRENT_TIME = datetime(2020, 1, 13, 2, tzinfo=timezone.utc)
MOCK_SLEEP = Mock()


@time_machine.travel(CURRENT_TIME)
@patch("hc.api.management.commands.sendreports.time.sleep", MOCK_SLEEP)
class SendReportsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        # Make alice eligible for a monthly report:
        self.profile.next_report_date = CURRENT_TIME - td(hours=1)
        # and for a nag
        self.profile.nag_period = td(hours=1)
        self.profile.next_nag_date = CURRENT_TIME - td(seconds=10)
        self.profile.save()

        # Disable bob's and charlie's monthly reports so they don't interfere
        self.bobs_profile.reports = "off"
        self.bobs_profile.save()

        self.charlies_profile.reports = "off"
        self.charlies_profile.save()

        # And it needs at least one check that has been pinged.
        self.check = Check(project=self.project, last_ping=now())
        self.check.created = datetime(2019, 10, 1, tzinfo=timezone.utc)
        self.check.name = "Foo"
        self.check.status = "down"
        self.check.save()

        self.flip = Flip(owner=self.check)
        self.flip.created = datetime(2019, 12, 31, 23, tzinfo=timezone.utc)
        self.flip.old_status = "new"
        self.flip.new_status = "down"
        self.flip.save()

    def test_it_sends_monthly_report(self) -> None:
        cmd = Command(stdout=Mock())
        found = cmd.handle_one_report()
        self.assertTrue(found)

        self.profile.refresh_from_db()
        assert self.profile.next_report_date
        self.assertEqual(self.profile.next_report_date.date(), date(2020, 2, 1))
        self.assertEqual(self.profile.next_report_date.day, 1)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Monthly Report")

    def test_it_obeys_next_report_date(self) -> None:
        self.profile.next_report_date = CURRENT_TIME + td(days=1)
        self.profile.save()

        found = Command().handle_one_report()
        self.assertFalse(found)

    def test_it_fills_blank_next_monthly_report_date(self) -> None:
        self.profile.next_report_date = None
        self.profile.save()

        found = Command().handle_one_report()
        self.assertTrue(found)

        self.profile.refresh_from_db()
        assert self.profile.next_report_date
        self.assertEqual(self.profile.next_report_date.date(), date(2020, 2, 1))
        self.assertEqual(len(mail.outbox), 0)

    def test_it_fills_blank_next_weekly_report_date(self) -> None:
        self.profile.reports = "weekly"
        self.profile.next_report_date = None
        self.profile.save()

        found = Command().handle_one_report()
        self.assertTrue(found)

        self.profile.refresh_from_db()
        assert self.profile.next_report_date
        self.assertEqual(self.profile.next_report_date.date(), date(2020, 1, 20))
        self.assertEqual(len(mail.outbox), 0)

    def test_it_obeys_reports_off(self) -> None:
        self.profile.reports = "off"
        self.profile.save()

        found = Command().handle_one_report()
        self.assertFalse(found)

    def test_it_requires_pinged_checks(self) -> None:
        self.check.delete()

        found = Command().handle_one_report()
        self.assertTrue(found)

        # No email should have been sent:
        self.assertEqual(len(mail.outbox), 0)

    def test_it_sends_nag(self) -> None:
        cmd = Command(stdout=Mock())
        found = cmd.handle_one_nag()
        self.assertTrue(found)

        self.profile.refresh_from_db()
        assert self.profile.next_nag_date
        self.assertTrue(self.profile.next_nag_date > CURRENT_TIME)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Reminder: 1 check still down")

    def test_it_obeys_next_nag_date(self) -> None:
        self.profile.next_nag_date = CURRENT_TIME + td(days=1)
        self.profile.save()

        # If next_nag_date is in future, a nag should not get sent.
        found = Command().handle_one_nag()
        self.assertFalse(found)

    def test_it_obeys_nag_period(self) -> None:
        self.profile.nag_period = td()
        self.profile.save()

        # If nag_period is 0 ("disabled"), a nag should not get sent.
        found = Command().handle_one_nag()
        self.assertFalse(found)

    def test_nags_require_down_checks(self) -> None:
        self.check.status = "up"
        self.check.save()

        found = Command().handle_one_nag()
        self.assertTrue(found)

        # No email should have been sent:
        self.assertEqual(len(mail.outbox), 0)

        # next_nag_date should now be unset
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.next_nag_date)
