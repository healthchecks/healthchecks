import logging
import sys
import time

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from hc.api.models import Check

logger = logging.getLogger(__name__)


def _stdout(message):
    sys.stdout.write(message)
    sys.stdout.flush()


def handle_one():
    """ Send an alert for a single check.

    Return True if an appropriate check was selected and processed.
    Return False if no checks need to be processed.

    """

    query = Check.objects.filter(user__isnull=False)

    now = timezone.now()
    going_down = Q(alert_after__lt=now, status="up")
    going_up = Q(alert_after__gt=now, status="down")
    query = query.filter(going_down | going_up)

    try:
        check = query[0]
    except IndexError:
        return False

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

    return True


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'

    def handle(self, *args, **options):

        ticks = 0
        while True:
            success = True
            while success:
                success = handle_one()
                ticks = 0 if success else ticks + 1

            time.sleep(1)
            _stdout(".")
            if ticks % 60 == 0:
                _stdout("\n")
