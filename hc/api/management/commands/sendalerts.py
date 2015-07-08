import sys
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from hc.api.models import Check
from hc.lib.emails import send_status_notification


def _log(message):
    sys.stdout.write(message)
    sys.stdout.flush()


class Command(BaseCommand):
    help = 'Ensures triggers exist in database'

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

                _log("\nSending email about going down for %s\n" % check.code)
                send_status_notification(check)
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

                _log("\nSending email about going up for %s\n" % check.code)
                send_status_notification(check)
                ticks = 0

                # Save status after the notification is sent
                check.save()

            time.sleep(1)
            ticks = (ticks + 1) % 80
            _log("." + ("\n" if ticks == 0 else ""))
