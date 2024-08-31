from __future__ import annotations

import signal
import time
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta as td
from io import TextIOBase
from threading import BoundedSemaphore
from types import FrameType
from typing import Any

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils.timezone import now

from hc.api.models import Check, Flip
from hc.lib.statsd import statsd


def notify(flip_id: int, stdout: TextIOBase) -> None:
    flip = Flip.objects.get(id=flip_id)
    check = flip.owner

    # Set or clear dates for followup nags
    check.project.update_next_nag_dates()

    if channels := flip.select_channels():
        # Transport classes should use flip's status, not check's status
        # (which can already be different by the time the notification goes out).
        # To make sure we catch template bugs, set check's status to an obnoxious,
        # invalid value:
        check.status = "IF_YOU_SEE_THIS_WE_HAVE_A_BUG"

        # Send notifications
        logs = []
        logs.append(f"{check.code} goes {flip.new_status}")
        send_start = now()
        for ch in channels:
            notify_start = time.time()
            error = ch.notify(flip)
            secs = time.time() - notify_start
            code8 = str(ch.code)[:8]
            if error:
                logs.append(f"  {code8} ({ch.kind}) Error in {secs:.1f}s: {error}")
            else:
                logs.append(f"  {code8} ({ch.kind}) OK in {secs:.1f}s")

        stdout.write("\n".join(logs))
        statsd.timing("hc.sendalerts.dwellTime", send_start - flip.created)
        statsd.timing("hc.sendalerts.sendTime", now() - send_start)


class Command(BaseCommand):
    help = "Sends UP/DOWN email alerts"

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.executor = ThreadPoolExecutor()
        self.seats = BoundedSemaphore(10)
        self.shutdown = False

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--num-workers",
            type=int,
            dest="num_workers",
            default=1,
            help="The number of concurrent worker processes to use",
        )

    def on_notify_done(self, future):
        close_old_connections()
        self.seats.release()

    def process_one_flip(self) -> bool:
        """Find unprocessed flip, send notifications.

        Return True if the main loop should continue without pausing:
        * if an unprocessed flip was found and submitted to executor.
        * or, if an unprocessed flip was found but another sendalerts process
          snatched it first.

        Return False if the main loop should wait a bit before continuing:
        * if all workers are currently busy
        * or, if there were no unprocessed flips in the database

        """

        if not self.seats.acquire(blocking=False):
            return False  # All workers are busy right now

        flip = Flip.objects.filter(processed=None).first()
        if flip is None:
            self.seats.release()
            return False

        q = Flip.objects.filter(id=flip.id, processed=None)
        num_updated = q.update(processed=now())
        if num_updated != 1:
            # Nothing got updated: another sendalerts process got there first.
            self.seats.release()
            return True

        f = self.executor.submit(notify, flip.id, self.stdout)
        f.add_done_callback(self.on_notify_done)
        return True

    def handle_going_down(self) -> bool:
        """Process a single check going down.

        1. Find a check with alert_after in the past, and status other than "down".
        2. Calculate its current status.
        3. If calculation throws an exception, push alert_after forward and re-raise.
        4. If the current status is not "down", update alert_after and return.
        5. Update the check's status in the database to "down".
        6. If exactly 1 row gets updated, create a Flip object.

        """

        q = Check.objects.filter(alert_after__lt=now()).exclude(status="down")
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
            q.update(alert_after=now() + td(hours=1))
            # Then re-raise the exception:
            raise e

        if status != "down":
            # It is not down yet. Update alert_after
            q.update(alert_after=check.going_down_after())
            return True

        flip_time = check.going_down_after()
        # In theory, going_down_after() can return None, but:
        # get_status() just reported status "down", so "going_down_after()"
        # must be able to calculate precisely when the check's state flipped.
        assert flip_time

        # Atomically update status
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

    def on_signal(self, signum: int, frame: FrameType | None) -> None:
        desc = signal.strsignal(signum)
        self.stdout.write(f"{desc}, finishing...\n")
        self.shutdown = True

    def handle(self, num_workers: int, **options: Any) -> str:
        self.seats = BoundedSemaphore(num_workers)
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGINT, self.on_signal)

        self.stdout.write("sendalerts is now running\n")
        sent = 0
        while not self.shutdown:
            # Create flips for any checks going down
            while self.handle_going_down():
                pass

            if self.process_one_flip():
                sent += 1
            else:
                # Sleep for 2 seconds, then look for more work
                time.sleep(2)

        self.executor.shutdown(wait=True)
        return f"Sent {sent} alert(s)."
