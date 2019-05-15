from datetime import timedelta as td

from django.core import mail
from django.utils.timezone import now
from hc.api.management.commands.sendreports import Command
from hc.api.models import Check
from hc.test import BaseTestCase
from mock import Mock


class SendAlertsTestCase(BaseTestCase):
    def setUp(self):
        super(SendAlertsTestCase, self).setUp()

        # Make alice eligible for reports:
        # account needs to be more than one month old
        self.alice.date_joined = now() - td(days=365)
        self.alice.save()

        # Make alice eligible for nags:
        self.profile.nag_period = td(hours=1)
        self.profile.next_nag_date = now() - td(seconds=10)
        self.profile.save()

        # And it needs at least one check that has been pinged.
        self.check = Check(project=self.project, last_ping=now())
        self.check.status = "down"
        self.check.save()

    def test_it_sends_report(self):
        cmd = Command()
        cmd.stdout = Mock()  # silence output to stdout
        cmd.pause = Mock()  # don't pause for 1s

        found = cmd.handle_one_monthly_report()
        self.assertTrue(found)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.next_report_date > now())
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertTrue("List-Unsubscribe" in email.extra_headers)

    def test_it_obeys_next_report_date(self):
        self.profile.next_report_date = now() + td(days=1)
        self.profile.save()

        found = Command().handle_one_monthly_report()
        self.assertFalse(found)

    def test_it_obeys_reports_allowed_flag(self):
        self.profile.reports_allowed = False
        self.profile.save()

        found = Command().handle_one_monthly_report()
        self.assertFalse(found)

    def test_it_requires_pinged_checks(self):
        self.check.delete()

        found = Command().handle_one_monthly_report()
        self.assertTrue(found)

        # No email should have been sent:
        self.assertEqual(len(mail.outbox), 0)

    def test_it_sends_nag(self):
        cmd = Command()
        cmd.stdout = Mock()  # silence output to stdout
        cmd.pause = Mock()  # don't pause for 1s

        found = cmd.handle_one_nag()
        self.assertTrue(found)

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.next_nag_date > now())
        self.assertEqual(len(mail.outbox), 1)

    def test_it_obeys_next_nag_date(self):
        self.profile.next_nag_date = now() + td(days=1)
        self.profile.save()

        # If next_nag_date is in future, a nag should not get sent.
        found = Command().handle_one_nag()
        self.assertFalse(found)

    def test_it_obeys_nag_period(self):
        self.profile.nag_period = td()
        self.profile.save()

        # If nag_period is 0 ("disabled"), a nag should not get sent.
        found = Command().handle_one_nag()
        self.assertFalse(found)

    def test_nags_require_down_checks(self):
        self.check.status = "up"
        self.check.save()

        found = Command().handle_one_nag()
        self.assertTrue(found)

        # No email should have been sent:
        self.assertEqual(len(mail.outbox), 0)

        # next_nag_date should now be unset
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.next_nag_date)
