import time
from threading import Thread

from django.core.management.base import BaseCommand
from django.utils import timezone
from hc.api.models import Check


def notify(check_id, stdout):
    check = Check.objects.get(id=check_id)
    tmpl = "Sending alert, status=%s, code=%s\n"
    stdout.write(tmpl % (check.status, check.code))

    # Set dates for followup nags
    if check.status == "down" and check.user.profile:
        check.user.profile.set_next_nag_date()

    # Send notifications
    errors = check.send_alert()
    for ch, error in errors:
        stdout.write("ERROR: %s %s %s\n" % (ch.kind, ch.value, error))


def notify_on_thread(check_id, stdout):
    t = Thread(target=notify, args=(check_id, stdout))
    t.start()


class Command(BaseCommand):
    help = 'Sends UP/DOWN email alerts'
    owned = Check.objects.filter(user__isnull=False).order_by("alert_after")

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-loop',
            action='store_false',
            dest='loop',
            default=True,
            help='Do not keep running indefinitely in a 2 second wait loop',
        )

        parser.add_argument(
            '--no-threads',
            action='store_false',
            dest='use_threads',
            default=False,
            help='Send alerts synchronously, without using threads',
        )

    def handle_one(self, use_threads=True):
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
                if use_threads:
                    notify_on_thread(check.id, self.stdout)
                else:
                    notify(check.id, self.stdout)

                return True

        return False

    def handle(self, use_threads=True, loop=True, *args, **options):
        self.stdout.write("sendalerts is now running\n")

        i, sent = 0, 0
        while True:
            while self.handle_one(use_threads):
                sent += 1

            if not loop:
                break

            time.sleep(2)
            i += 1
            if i % 60 == 0:
                timestamp = timezone.now().isoformat()
                self.stdout.write("-- MARK %s --\n" % timestamp)

        return "Sent %d alert(s)" % sent
