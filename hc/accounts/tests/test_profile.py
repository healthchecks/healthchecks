from datetime import timedelta as td
from django.core import mail

from django.conf import settings
from django.utils.timezone import now
from hc.test import BaseTestCase
from hc.api.models import Check


class ProfileTestCase(BaseTestCase):
    def test_it_sends_set_password_link(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"set_password": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 302

        # profile.token should be set now
        self.profile.refresh_from_db()
        token = self.profile.token
        self.assertTrue(len(token) > 10)

        # And an email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        expected_subject = "Set password on %s" % settings.SITE_NAME
        self.assertEqual(mail.outbox[0].subject, expected_subject)

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

    def test_it_sends_change_email_link(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"change_email": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 302

        # profile.token should be set now
        self.profile.refresh_from_db()
        token = self.profile.token
        self.assertTrue(len(token) > 10)

        # And an email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        expected_subject = "Change email address on %s" % settings.SITE_NAME
        self.assertEqual(mail.outbox[0].subject, expected_subject)

    def test_leaving_works(self):
        self.client.login(username="bob@example.org", password="password")

        form = {"code": str(self.project.code), "leave_project": "1"}
        r = self.client.post("/accounts/profile/", form)
        self.assertContains(r, "Left project")
        self.assertNotContains(r, "Alice's Project")

        self.bobs_profile.refresh_from_db()
        self.assertIsNone(self.bobs_profile.current_project)
        self.assertFalse(self.bob.memberships.exists())

    def test_leaving_checks_membership(self):
        self.client.login(username="charlie@example.org", password="password")

        form = {"code": str(self.project.code), "leave_project": "1"}
        r = self.client.post("/accounts/profile/", form)
        self.assertEqual(r.status_code, 400)
