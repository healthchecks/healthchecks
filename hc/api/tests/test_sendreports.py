from datetime import timedelta as td

from django.utils.timezone import now
from hc.api.management.commands.sendreports import Command
from hc.api.models import Check
from hc.test import BaseTestCase


class SendAlertsTestCase(BaseTestCase):

    def setUp(self):
        super(SendAlertsTestCase, self).setUp()

        # Make alice eligible for reports:
        # account needs to be more than one month old
        self.alice.date_joined = now() - td(days=365)
        self.alice.save()

        # And it needs at least one check that has been pinged.
        self.check = Check(user=self.alice, last_ping=now())
        self.check.save()

    def test_it_sends_report(self):
        sent = Command().handle_one_run()
        self.assertEqual(sent, 1)

        # Alice's profile should have been updated
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.next_report_date > now())

    def test_it_obeys_next_report_date(self):
        self.profile.next_report_date = now() + td(days=1)
        self.profile.save()

        sent = Command().handle_one_run()
        self.assertEqual(sent, 0)

    def test_it_obeys_reports_allowed_flag(self):
        self.profile.reports_allowed = False
        self.profile.save()

        sent = Command().handle_one_run()
        self.assertEqual(sent, 0)

    def test_it_requires_pinged_checks(self):
        self.check.delete()

        sent = Command().handle_one_run()
        self.assertEqual(sent, 0)
