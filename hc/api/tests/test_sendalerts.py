from datetime import timedelta
from mock import Mock, patch

from django.core.management import call_command
from django.utils.timezone import now
from hc.api.management.commands.sendalerts import Command, notify
from hc.api.models import Check
from hc.test import BaseTestCase


class SendAlertsTestCase(BaseTestCase):

    def test_it_handles_grace_period(self):
        check = Check(user=self.alice, status="up")
        # 1 day 30 minutes after ping the check is in grace period:
        check.last_ping = now() - timedelta(days=1, minutes=30)
        check.alert_after = check.get_alert_after()
        check.save()

        # Expect no exceptions--
        Command().handle_one()

    @patch("hc.api.management.commands.sendalerts.notify_on_thread")
    def test_it_notifies_when_check_goes_down(self, mock_notify):
        check = Check(user=self.alice, status="up")
        check.last_ping = now() - timedelta(days=2)
        check.alert_after = check.get_alert_after()
        check.save()

        result = Command().handle_one()

        # If it finds work, it should return True
        self.assertTrue(result)

        # It should change stored status to "down"
        check.refresh_from_db()
        self.assertEqual(check.status, "down")

        # It should call `notify_on_thread`
        self.assertTrue(mock_notify.called)

    @patch("hc.api.management.commands.sendalerts.notify_on_thread")
    def test_it_notifies_when_check_goes_up(self, mock_notify):
        check = Check(user=self.alice, status="down")
        check.last_ping = now()
        check.alert_after = check.get_alert_after()
        check.save()

        result = Command().handle_one()

        # If it finds work, it should return True
        self.assertTrue(result)

        # It should change stored status to "up"
        check.refresh_from_db()
        self.assertEqual(check.status, "up")

        # It should call `notify_on_thread`
        self.assertTrue(mock_notify.called)

        # alert_after now should be set
        self.assertTrue(check.alert_after)

    @patch("hc.api.management.commands.sendalerts.notify_on_thread")
    def test_it_updates_alert_after(self, mock_notify):
        check = Check(user=self.alice, status="up")
        check.last_ping = now() - timedelta(hours=1)
        check.alert_after = check.last_ping
        check.save()

        result = Command().handle_one()

        # If it finds work, it should return True
        self.assertTrue(result)

        # It should change stored status to "down"
        check.refresh_from_db()

        # alert_after should have been increased
        self.assertTrue(check.alert_after > check.last_ping)

        # notify_on_thread should *not* have been called
        self.assertFalse(mock_notify.called)

    @patch("hc.api.management.commands.sendalerts.notify")
    def test_it_works_synchronously(self, mock_notify):
        check = Check(user=self.alice, status="up")
        check.last_ping = now() - timedelta(days=2)
        check.alert_after = check.get_alert_after()
        check.save()

        call_command("sendalerts", loop=False, use_threads=False)

        # It should call `notify` instead of `notify_on_thread`
        self.assertTrue(mock_notify.called)

    def test_it_updates_owners_next_nag_date(self):
        self.profile.nag_period = timedelta(hours=1)
        self.profile.save()

        check = Check(user=self.alice, status="down")
        check.last_ping = now() - timedelta(days=2)
        check.alert_after = check.get_alert_after()
        check.save()

        notify(check.id, Mock())

        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.next_nag_date)

    def test_it_updates_members_next_nag_date(self):
        self.bobs_profile.nag_period = timedelta(hours=1)
        self.bobs_profile.save()

        check = Check(user=self.alice, status="down")
        check.last_ping = now() - timedelta(days=2)
        check.alert_after = check.get_alert_after()
        check.save()

        notify(check.id, Mock())

        self.bobs_profile.refresh_from_db()
        self.assertIsNotNone(self.bobs_profile.next_nag_date)

    def test_it_does_not_touch_already_set_next_nag_dates(self):
        original_nag_date = now() - timedelta(minutes=30)
        self.profile.nag_period = timedelta(hours=1)
        self.profile.next_nag_date = original_nag_date
        self.profile.save()

        check = Check(user=self.alice, status="down")
        check.last_ping = now() - timedelta(days=2)
        check.alert_after = check.get_alert_after()
        check.save()

        notify(check.id, Mock())

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.next_nag_date, original_nag_date)