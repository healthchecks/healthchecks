import logging
import sys
import time

from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Q
from django.utils import timezone
from hc.api.models import Check

executor = ThreadPoolExecutor(max_workers=10)
logger = logging.getLogger(__name__)


def _stdout(message):
    sys.stdout.write(message)
    sys.stdout.flush()


def handle_many():
    """ Send alerts for many checks simultaneously. """
    query = Check.objects.filter(user__isnull=False)

    now = timezone.now()
    going_down = Q(alert_after__lt=now, status="up")
    going_up = Q(alert_after__gt=now, status="down")
    query = query.filter(going_down | going_up)
    checks = list(query.iterator())
    if not checks:
        return False

    for future in [executor.submit(handle_one, check) for check in checks]:
        future.result()

    return True


def handle_one(check):
    """ Send an alert for a single check.

    Return True if an appropriate check was selected and processed.
    Return False if no checks need to be processed.

    """
    check.status = check.get_status()

    tmpl = "\nSending alert, status=%s, code=%s\n"
    _stdout(tmpl % (check.status, check.code))

    try:
        check.send_alert()
    except:
        # Catch EVERYTHING. If we crash here, what can happen is:
        # - the sendalerts command will crash
        # - supervisor will respawn sendalerts command
        # - sendalerts will try same thing again, resulting in infinite loop
        # So instead we catch and log all exceptions, and mark
        # the checks as paused so they are not retried.
        logger.error("Could not alert %s" % check.code, exc_info=True)
        check.status = "paused"
    finally:
        check.save()
        connection.close()

    return True


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'

    def handle(self, *args, **options):

        ticks = 0
        while True:
            if handle_many():
                ticks = 0
            else:
                ticks += 1

            time.sleep(1)
            _stdout(".")
            if ticks % 60 == 0:
                _stdout("\n")
