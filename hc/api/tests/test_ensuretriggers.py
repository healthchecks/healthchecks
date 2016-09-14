from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from hc.api.management.commands.ensuretriggers import Command
from hc.api.models import Check


class EnsureTriggersTestCase(TestCase):

    def test_ensure_triggers(self):
        Command().handle()

        check = Check.objects.create()
        assert check.alert_after is None

        check.last_ping = timezone.now()
        check.save()
        check.refresh_from_db()
        assert check.alert_after is not None
        ### The above assert fails. Make it pass

        alert_after = check.alert_after

        check.last_ping += timedelta(days=1)
        check.save()
        check.refresh_from_db()
        ### Assert that alert_after is lesser than the check's alert_after 
