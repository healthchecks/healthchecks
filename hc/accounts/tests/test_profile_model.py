from datetime import timedelta as td

from django.core import mail
from django.utils.timezone import now
from hc.test import BaseTestCase
from hc.api.models import Check


class ProfileModelTestCase(BaseTestCase):
    def test_it_sends_report(self):
        check = Check(project=self.project, name="Test Check")
        check.last_ping = now()
        check.save()

        sent = self.profile.send_report()
        self.assertTrue(sent)

        # And an email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertEqual(message.subject, "Monthly Report")
        self.assertIn("Test Check", message.body)

    def test_it_skips_report_if_no_pings(self):
        check = Check(project=self.project, name="Test Check")
        check.save()

        sent = self.profile.send_report()
        self.assertFalse(sent)

        self.assertEqual(len(mail.outbox), 0)

    def test_it_skips_report_if_no_recent_pings(self):
        check = Check(project=self.project, name="Test Check")
        check.last_ping = now() - td(days=365)
        check.save()

        sent = self.profile.send_report()
        self.assertFalse(sent)

        self.assertEqual(len(mail.outbox), 0)

    def test_it_sends_nag(self):
        check = Check(project=self.project, name="Test Check")
        check.status = "down"
        check.last_ping = now()
        check.save()

        self.profile.nag_period = td(hours=1)
        self.profile.save()

        sent = self.profile.send_report(nag=True)
        self.assertTrue(sent)

        # And an email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertEqual(message.subject, "Reminder: 1 check still down")
        self.assertIn("Test Check", message.body)

    def test_it_skips_nag_if_none_down(self):
        check = Check(project=self.project, name="Test Check")
        check.last_ping = now()
        check.save()

        self.profile.nag_period = td(hours=1)
        self.profile.save()

        sent = self.profile.send_report(nag=True)
        self.assertFalse(sent)

        self.assertEqual(len(mail.outbox), 0)

    def test_it_sets_next_nag_date(self):
        Check.objects.create(project=self.project, status="down")

        self.profile.nag_period = td(hours=1)
        self.profile.update_next_nag_date()

        self.assertTrue(self.profile.next_nag_date)

    def test_it_does_not_set_next_nag_date_if_no_nag_period(self):
        Check.objects.create(project=self.project, status="down")
        self.profile.update_next_nag_date()
        self.assertIsNone(self.profile.next_nag_date)

    def test_it_does_not_update_existing_next_nag_date(self):
        Check.objects.create(project=self.project, status="down")

        original_nag_date = now() - td(minutes=30)

        self.profile.next_nag_date = original_nag_date
        self.profile.nag_period = td(hours=1)
        self.profile.update_next_nag_date()

        self.assertEqual(self.profile.next_nag_date, original_nag_date)

    def test_it_clears_next_nag_date(self):
        self.profile.next_nag_date = now()
        self.profile.update_next_nag_date()
        self.assertIsNone(self.profile.next_nag_date)
