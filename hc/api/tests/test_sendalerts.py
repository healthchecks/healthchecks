from datetime import timedelta as td
from io import StringIO
from mock import Mock, patch

from django.core.management import call_command
from django.utils.timezone import now
from hc.api.management.commands.sendalerts import Command, notify
from hc.api.models import Flip, Check
from hc.test import BaseTestCase


class SendAlertsTestCase(BaseTestCase):
    def test_it_handles_grace_period(self):
        check = Check(project=self.project, status="up")
        # 1 day 30 minutes after ping the check is in grace period:
        check.last_ping = now() - td(days=1, minutes=30)
        check.alert_after = check.last_ping + td(days=1, hours=1)
        check.save()

        Command().handle_going_down()

        check.refresh_from_db()
        self.assertEqual(check.status, "up")
        self.assertEqual(Flip.objects.count(), 0)

    def test_it_creates_a_flip_when_check_goes_down(self):
        check = Check(project=self.project, status="up")
        check.last_ping = now() - td(days=2)
        check.alert_after = check.last_ping + td(days=1, hours=1)
        check.save()

        result = Command().handle_going_down()

        # If it finds work, it should return True
        self.assertTrue(result)

        # It should create a flip object
        flip = Flip.objects.get()
        self.assertEqual(flip.owner_id, check.id)
        self.assertEqual(flip.created, check.alert_after)
        self.assertEqual(flip.new_status, "down")

        # It should change stored status to "down", and clear out alert_after
        check.refresh_from_db()
        self.assertEqual(check.status, "down")
        self.assertEqual(check.alert_after, None)

    @patch("hc.api.management.commands.sendalerts.notify_on_thread")
    def test_it_processes_flip(self, mock_notify):
        check = Check(project=self.project, status="up")
        check.last_ping = now()
        check.alert_after = check.last_ping + td(days=1, hours=1)
        check.save()

        flip = Flip(owner=check, created=check.last_ping)
        flip.old_status = "down"
        flip.new_status = "up"
        flip.save()

        result = Command().process_one_flip()

        # If it finds work, it should return True
        self.assertTrue(result)

        # It should set the processed date
        flip.refresh_from_db()
        self.assertTrue(flip.processed)

        # It should call `notify_on_thread`
        self.assertTrue(mock_notify.called)

    @patch("hc.api.management.commands.sendalerts.notify_on_thread")
    def test_it_updates_alert_after(self, mock_notify):
        check = Check(project=self.project, status="up")
        check.last_ping = now() - td(hours=1)
        check.alert_after = check.last_ping
        check.save()

        result = Command().handle_going_down()

        # If it finds work, it should return True
        self.assertTrue(result)

        # alert_after should have been increased
        expected_aa = check.last_ping + td(days=1, hours=1)
        check.refresh_from_db()
        self.assertEqual(check.alert_after, expected_aa)

        # a flip should have not been created
        self.assertEqual(Flip.objects.count(), 0)

    @patch("hc.api.management.commands.sendalerts.notify")
    def test_it_works_synchronously(self, mock_notify):
        check = Check(project=self.project, status="up")
        check.last_ping = now() - td(days=2)
        check.alert_after = check.last_ping + td(days=1, hours=1)
        check.save()

        call_command("sendalerts", loop=False, use_threads=False, stdout=StringIO())

        # It should call `notify` instead of `notify_on_thread`
        self.assertTrue(mock_notify.called)

    def test_it_updates_owners_next_nag_date(self):
        self.profile.nag_period = td(hours=1)
        self.profile.save()

        check = Check(project=self.project, status="down")
        check.last_ping = now() - td(days=2)
        check.save()

        flip = Flip(owner=check, created=check.last_ping)
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        notify(flip.id, Mock())

        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.next_nag_date)

    def test_it_updates_members_next_nag_date(self):
        self.bobs_profile.nag_period = td(hours=1)
        self.bobs_profile.save()

        check = Check(project=self.project, status="down")
        check.last_ping = now() - td(days=2)
        check.save()

        flip = Flip(owner=check, created=check.last_ping)
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        notify(flip.id, Mock())

        self.bobs_profile.refresh_from_db()
        self.assertIsNotNone(self.bobs_profile.next_nag_date)

    def test_it_does_not_touch_already_set_next_nag_dates(self):
        original_nag_date = now() - td(minutes=30)
        self.profile.nag_period = td(hours=1)
        self.profile.next_nag_date = original_nag_date
        self.profile.save()

        check = Check(project=self.project, status="down")
        check.last_ping = now() - td(days=2)
        check.save()

        flip = Flip(owner=check, created=check.last_ping)
        flip.old_status = "up"
        flip.new_status = "down"
        flip.save()

        notify(flip.id, Mock())

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.next_nag_date, original_nag_date)
