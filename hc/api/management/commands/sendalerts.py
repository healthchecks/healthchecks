from __future__ import annotations

import signal
import time
from datetime import timedelta as td
from threading import Thread

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from statsd.defaults.env import statsd

from hc.api.models import Check, Flip

SENDING_TMPL = "Sending alert, status=%s, code=%s\n"
SEND_TIME_TMPL = "Sending took %.1fs, code=%s\n"


def notify(flip_id, stdout):
    flip = Flip.objects.get(id=flip_id)

    check = flip.owner
    # Set the historic status here but *don't save it*.
    # It would be nicer to pass the status explicitly, as a separate parameter.
    check.status = flip.new_status
    # And just to make sure it doesn't get saved by a future coding accident:
    setattr(check, "save", None)

    stdout.write(SENDING_TMPL % (flip.new_status, check.code))

    # Set or clear dates for followup nags
    check.project.update_next_nag_dates()

    # Send notifications
    send_start = now()

    for ch, error, secs in flip.send_alerts():
        label = "OK"
        if error:
            label = "ERROR"
        elif secs > 5:
            label = "SLOW"

        s = " * %-5s %4.1fs %-10s %s %s\n" % (label, secs, ch.kind, ch.code, error)
        stdout.write(s)

    send_time = now() - send_start
    stdout.write(SEND_TIME_TMPL % (send_time.total_seconds(), check.code))

    statsd.timing("hc.sendalerts.dwellTime", send_start - flip.created)
    statsd.timing("hc.sendalerts.sendTime", send_time)


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
        """Find unprocessed flip, send notifications."""

        # Order by processed, otherwise Django will automatically order by id
        # and make the query less efficient
        q = Flip.objects.filter(processed=None).order_by("processed")
        flip = q.first()
        if flip is None:
            return False

        q = Flip.objects.filter(id=flip.id, processed=None)
        num_updated = q.update(processed=now())
        if num_updated != 1:
            # Nothing got updated: another worker process got there first.
            return True

        if use_threads:
            notify_on_thread(flip.id, self.stdout)
        else:
            notify(flip.id, self.stdout)

        return True

    def handle_going_down(self):
        """Process a single check going down."""

        now_value = now()

        q = Check.objects.filter(alert_after__lt=now_value).exclude(status="down")
        # Sort by alert_after, to avoid unnecessary sorting by id:
        check = q.order_by("alert_after").first()
        if check is None:
            return False

        old_status = check.status
        q = Check.objects.filter(id=check.id, status=old_status)

        try:
            status = check.get_status()
        except Exception as e:
            # Make sure we don't trip on this check again for an hour:
            # Otherwise sendalerts may end up in a crash loop.
            q.update(alert_after=now_value + td(hours=1))
            # Then re-raise the exception:
            raise e

        if status != "down":
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

    def on_signal(self, signum, frame):
        desc = signal.strsignal(signum)
        self.stdout.write(f"{desc}, finishing...\n")
        self.shutdown = True

    def handle(self, use_threads=True, loop=True, *args, **options):
        self.shutdown = False
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGINT, self.on_signal)

        self.stdout.write("sendalerts is now running\n")
        sent = 0
        while not self.shutdown:
            # Create flips for any checks going down
            while not self.shutdown and self.handle_going_down():
                pass

            # Process the unprocessed flips
            while not self.shutdown and self.process_one_flip(use_threads):
                sent += 1

            if not loop:
                break

            # Sleep for 2 seconds before looking for more work
            if not self.shutdown:
                time.sleep(2)

        return f"Sent {sent} alert(s)."
