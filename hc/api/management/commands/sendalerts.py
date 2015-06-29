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

        while True:
            # Gone down?
            query = Check.objects
            query = query.filter(alert_after__lt=timezone.now())
            query = query.filter(status="up")
            for check in query:
                check.status = "down"
                check.save()

                _log("\nSending email about going down for %s\n" % check.code)
                send_status_notification(check)

            # Gone up?
            query = Check.objects
            query = query.filter(alert_after__gt=timezone.now())
            query = query.filter(status="down")
            for check in query:
                check.status = "up"
                check.save()

                _log("\nSending email about going up for %s\n" % check.code)
                send_status_notification(check)

            time.sleep(1)
            _log(".")
