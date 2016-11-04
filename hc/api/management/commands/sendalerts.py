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


def notify_on_thread(check_id, stdout):
    t = Thread(target=notify, args=(check_id, stdout))
    t.start()


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'
    owned = Check.objects.filter(user__isnull=False)

    def handle_one(self):
        """ Process a single check.  """

        now = timezone.now()

        # Look for checks that are going down
        q = self.owned.filter(alert_after__lt=now, status="up")
        check = q.first()

        # If none found, look for checks that are going up
        if not check:
            q = self.owned.filter(alert_after__gt=now, status="down")
            check = q.first()

        if check is None:
            return False

        q = Check.objects.filter(id=check.id, status=check.status)
        current_status = check.get_status()
        if check.status == current_status:
            # Stored status is already up-to-date. Update alert_after
            # as needed but don't send notifications
            q.update(alert_after=check.get_alert_after())
            return True
        else:
            # Atomically update status to the opposite
            num_updated = q.update(status=current_status)
            if num_updated == 1:
                # Send notifications only if status update succeeded
                # (no other sendalerts process got there first)
                notify_on_thread(check.id, self.stdout)
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
