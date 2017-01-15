from datetime import timedelta

from django.utils import timezone
from hc.api.management.commands.sendreports import Command
from hc.api.models import Check
from hc.test import BaseTestCase


class SendAlertsTestCase(BaseTestCase):

    def test_it_sends_report(self):
        # Make alice eligible for reports
        self.alice.date_joined = timezone.now() - timedelta(days=365)
        self.alice.save()

        check = Check(user=self.alice, last_ping=timezone.now())
        check.save()

        sent = Command().handle_one_run()
        self.assertEqual(sent, 1)
