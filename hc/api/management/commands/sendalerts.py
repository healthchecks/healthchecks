import time
from threading import Thread

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from hc.api.models import Check


def notify(check_id, stdout):
    check = Check.objects.get(id=check_id)

    tmpl = "\nSending alert, status=%s, code=%s\n"
    stdout.write(tmpl % (check.status, check.code))
    errors = check.send_alert()
    for ch, error in errors:
        stdout.write("ERROR: %s %s %s\n" % (ch.kind, ch.value, error))


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'
    owned = Check.objects.filter(user__isnull=False)

    def handle_one(self):
        """ Process a single check.  """

        now = timezone.now()

        # Look for checks that are going down
        flipped = "down"
        q = self.owned.filter(alert_after__lt=now, status="up")
        check = q.first()

        if not check:
            # If none found, look for checks that are going up
            flipped = "up"
            q = self.owned.filter(alert_after__gt=now, status="down")
            check = q.first()

        if check:
            # Atomically update status to the opposite
            q = Check.objects.filter(id=check.id, status=check.status)
            num_updated = q.update(status=flipped)
            if num_updated == 1:
                # Send notifications only if status update succeeded
                # (no other sendalerts process got there first)
                t = Thread(target=notify, args=(check.id, self.stdout))
                t.start()
                return True

        return False

    def handle(self, *args, **options):
        self.stdout.write("sendalerts is now running")

        ticks = 0
        while True:

            while self.handle_one():
                ticks = 0

            ticks += 1
            time.sleep(2)
            if ticks % 60 == 0:
                formatted = timezone.now().isoformat()
                self.stdout.write("-- MARK %s --" % formatted)

            connection.close()
