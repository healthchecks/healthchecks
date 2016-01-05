import logging
import time

from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from hc.api.models import Check

executor = ThreadPoolExecutor(max_workers=10)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'

    def handle_many(self):
        """ Send alerts for many checks simultaneously. """
        query = Check.objects.filter(user__isnull=False).select_related("user")

        now = timezone.now()
        going_down = query.filter(alert_after__lt=now, status="up")
        going_up = query.filter(alert_after__gt=now, status="down")
        # Don't combine this in one query so Postgres can query using index:
        checks = list(going_down.iterator()) + list(going_up.iterator())
        if not checks:
            return False

        futures = [executor.submit(self.handle_one, check) for check in checks]
        for future in futures:
            future.result()

        return True

    def handle_one(self, check):
        """ Send an alert for a single check.

        Return True if an appropriate check was selected and processed.
        Return False if no checks need to be processed.

        """
        check.status = check.get_status()

        tmpl = "\nSending alert, status=%s, code=%s\n"
        self.stdout.write(tmpl % (check.status, check.code))

        try:
            check.send_alert()
        except:
            # Catch EVERYTHING. If we crash here, what can happen is:
            # - the sendalerts command will crash
            # - supervisor will respawn sendalerts command
            # - sendalerts will try same thing again, resulting in
            #   infinite loop
            # So instead we catch and log all exceptions, and mark
            # the checks as paused so they are not retried.
            logger.error("Could not alert %s" % check.code, exc_info=True)
            check.status = "paused"
        finally:
            check.save()
            connection.close()

        return True

    def handle(self, *args, **options):
        self.stdout.write("sendalerts starts up")

        ticks = 0
        while True:
            if self.handle_many():
                ticks = 0
            else:
                ticks += 1

            time.sleep(1)
            if ticks % 60 == 0:
                formatted = timezone.now().isoformat()
                self.stdout.write("-- MARK %s --" % formatted)
