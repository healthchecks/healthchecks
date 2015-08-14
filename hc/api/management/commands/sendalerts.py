import sys
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from hc.api.models import Check


def _log(message):
    sys.stdout.write(message)
    sys.stdout.flush()


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'

    def handle(self, *args, **options):

        ticks = 0
        while True:
            # Gone down?
            query = Check.objects
            query = query.filter(alert_after__lt=timezone.now())
            query = query.filter(user__isnull=False)
            query = query.filter(status="up")
            for check in query:
                check.status = "down"

                _log("\nSending notification(s) about going down for %s\n" % check.code)
                check.send_alert()
                ticks = 0

                # Save status after the notification is sent
                check.save()

            # Gone up?
            query = Check.objects
            query = query.filter(alert_after__gt=timezone.now())
            query = query.filter(user__isnull=False)
            query = query.filter(status="down")
            for check in query:
                check.status = "up"

                _log("\nSending notification(s) about going up for %s\n" % check.code)
                check.send_alert()
                ticks = 0

                # Save status after the notification is sent
                check.save()

            time.sleep(1)
            ticks = (ticks + 1) % 80
            _log("." + ("\n" if ticks == 0 else ""))
