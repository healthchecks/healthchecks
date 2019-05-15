import time
from threading import Thread

from django.core.management.base import BaseCommand
from django.utils import timezone
from hc.api.models import Check, Flip


def notify(flip_id, stdout):
    flip = Flip.objects.get(id=flip_id)

    check = flip.owner
    # Set the historic status here but *don't save it*.
    # It would be nicer to pass the status explicitly, as a separate parameter.
    check.status = flip.new_status
    # And just to make sure it doesn't get saved by a future coding accident:
    setattr(check, "save", None)

    tmpl = "Sending alert, status=%s, code=%s\n"
    stdout.write(tmpl % (flip.new_status, check.code))

    # Set dates for followup nags
    if flip.new_status == "down":
        check.project.set_next_nag_date()

    # Send notifications
    errors = flip.send_alerts()
    for ch, error in errors:
        stdout.write("ERROR: %s %s %s\n" % (ch.kind, ch.value, error))


def notify_on_thread(flip_id, stdout):
    t = Thread(target=notify, args=(flip_id, stdout))
    t.start()


class Command(BaseCommand):
    help = "Sends UP/DOWN email alerts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-loop",
            action="store_false",
            dest="loop",
            default=True,
            help="Do not keep running indefinitely in a 2 second wait loop",
        )

        parser.add_argument(
            "--no-threads",
            action="store_false",
            dest="use_threads",
            default=False,
            help="Send alerts synchronously, without using threads",
        )

    def process_one_flip(self, use_threads=True):
        """ Find unprocessed flip, send notifications.  """

        # Order by processed, otherwise Django will automatically order by id
        # and make the query less efficient
        q = Flip.objects.filter(processed=None).order_by("processed")
        flip = q.first()
        if flip is None:
            return False

        q = Flip.objects.filter(id=flip.id, processed=None)
        num_updated = q.update(processed=timezone.now())
        if num_updated != 1:
            # Nothing got updated: another worker process got there first.
            return True

        if use_threads:
            notify_on_thread(flip.id, self.stdout)
        else:
            notify(flip.id, self.stdout)

        return True

    def handle_going_down(self):
        """ Process a single check going down.  """

        now = timezone.now()

        # In PostgreSQL, add this index to run the below query efficiently:
        # CREATE INDEX api_check_up ON api_check (alert_after) WHERE status = 'up'

        q = Check.objects.filter(alert_after__lt=now).exclude(status="down")
        # Sort by alert_after, to avoid unnecessary sorting by id:
        check = q.order_by("alert_after").first()
        if check is None:
            return False

        old_status = check.status
        q = Check.objects.filter(id=check.id, status=old_status)

        if check.get_status(with_started=False) != "down":
            # It is not down yet. Update alert_after
            q.update(alert_after=check.going_down_after())
            return True

        # Atomically update status
        flip_time = check.going_down_after()
        num_updated = q.update(alert_after=None, status="down")
        if num_updated != 1:
            # Nothing got updated: another worker process got there first.
            return True

        flip = Flip(owner=check)
        flip.created = flip_time
        flip.old_status = old_status
        flip.new_status = "down"
        flip.save()

        return True

    def handle(self, use_threads=True, loop=True, *args, **options):
        self.stdout.write("sendalerts is now running\n")

        i, sent = 0, 0
        while True:
            # Create flips for any checks going down
            while self.handle_going_down():
                pass

            # Process the unprocessed flips
            while self.process_one_flip(use_threads):
                sent += 1

            if not loop:
                break

            time.sleep(2)
            i += 1
            if i % 60 == 0:
                timestamp = timezone.now().isoformat()
                self.stdout.write("-- MARK %s --\n" % timestamp)

        return "Sent %d alert(s)" % sent
