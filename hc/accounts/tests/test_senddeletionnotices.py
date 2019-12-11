from datetime import timedelta as td

from django.core import mail
from django.utils.timezone import now
from hc.accounts.management.commands.senddeletionnotices import Command
from hc.accounts.models import Member
from hc.api.models import Check, Ping
from hc.test import BaseTestCase
from mock import Mock


class SendDeletionNoticesTestCase(BaseTestCase):
    def setUp(self):
        super(SendDeletionNoticesTestCase, self).setUp()

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
        self.assertEqual(result, "Done! Sent 1 notices")

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.deletion_notice_date)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Inactive Account Notification")

    def test_it_checks_last_login(self):
        # alice has logged in recently:
        self.alice.last_login = now() - td(days=15)
        self.alice.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(result, "Done! Sent 0 notices")

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_date_joined(self):
        # alice signed up recently:
        self.alice.date_joined = now() - td(days=15)
        self.alice.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(result, "Done! Sent 0 notices")

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_deletion_notice_date(self):
        # alice has already received a deletion notice
        self.profile.deletion_notice_date = now() - td(days=15)
        self.profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(result, "Done! Sent 0 notices")

    def test_it_checks_sms_limit(self):
        # alice has a paid account
        self.profile.sms_limit = 50
        self.profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(result, "Done! Sent 0 notices")

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_team_members(self):
        # bob has access to alice's project
        Member.objects.create(user=self.bob, project=self.project)

        result = Command(stdout=Mock()).handle()
        self.assertEqual(result, "Done! Sent 0 notices")

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_recent_pings(self):
        check = Check.objects.create(project=self.project)
        Ping.objects.create(owner=check)

        result = Command(stdout=Mock()).handle()
        self.assertEqual(result, "Done! Sent 0 notices")

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deletion_notice_date)

    def test_it_checks_last_active_date(self):
        # alice has been browsing the site recently
        self.profile.last_active_date = now() - td(days=15)
        self.profile.save()

        result = Command(stdout=Mock()).handle()
        self.assertEqual(result, "Done! Sent 0 notices")
