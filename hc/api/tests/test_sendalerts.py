from datetime import timedelta
from mock import patch

from django.utils import timezone
from hc.api.management.commands.sendalerts import Command
from hc.api.models import Check
from hc.test import BaseTestCase


class SendAlertsTestCase(BaseTestCase):

    def test_it_handles_grace_period(self):
        check = Check(user=self.alice, status="up")
        # 1 day 30 minutes after ping the check is in grace period:
        check.last_ping = timezone.now() - timedelta(days=1, minutes=30)
        check.alert_after = check.get_alert_after()
        check.save()

        # Expect no exceptions--
        Command().handle_one()

    @patch("hc.api.management.commands.sendalerts.notify_on_thread")
    def test_it_notifies_when_check_goes_down(self, mock_notify):
        check = Check(user=self.alice, status="up")
        check.last_ping = timezone.now() - timedelta(days=2)
        check.alert_after = check.get_alert_after()
        check.save()

        result = Command().handle_one()

        # If it finds work, it should return True
        self.assertTrue(result)

        # It should change stored status to "down"
        check.refresh_from_db()
        self.assertEqual(check.status, "down")

        # It should call `notify`
        self.assertTrue(mock_notify.called)

    @patch("hc.api.management.commands.sendalerts.notify_on_thread")
    def test_it_notifies_when_check_goes_up(self, mock_notify):
        check = Check(user=self.alice, status="down")
        check.last_ping = timezone.now()
        check.alert_after = check.get_alert_after()
        check.save()

        result = Command().handle_one()

        # If it finds work, it should return True
        self.assertTrue(result)

        # It should change stored status to "up"
        check.refresh_from_db()
        self.assertEqual(check.status, "up")

        # It should call `notify`
        self.assertTrue(mock_notify.called)

        # alert_after now should be set
        self.assertTrue(check.alert_after)

    @patch("hc.api.management.commands.sendalerts.notify_on_thread")
    def test_it_updates_alert_after(self, mock_notify):
        check = Check(user=self.alice, status="up")
        check.last_ping = timezone.now() - timedelta(hours=1)
        check.alert_after = check.last_ping
        check.save()

        result = Command().handle_one()

        # If it finds work, it should return True
        self.assertTrue(result)

        # It should change stored status to "down"
        check.refresh_from_db()

        # alert_after should have been increased
        self.assertTrue(check.alert_after > check.last_ping)

        # notify should *not* have been called
        self.assertFalse(mock_notify.called)
