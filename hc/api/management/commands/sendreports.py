from __future__ import annotations

import signal
import time
from argparse import ArgumentParser
from types import FrameType
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.timezone import now

from hc.accounts.models import NO_NAG, Profile


class Command(BaseCommand):
    help = "Send due monthly reports and nags"
    tmpl = "Sent monthly report to %s"

    def pause(self) -> None:
        time.sleep(3)

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--loop",
            action="store_true",
            dest="loop",
            default=False,
            help="Keep running indefinitely in a 300 second wait loop",
        )

    def handle_one_report(self) -> bool:
        report_due = Q(next_report_date__lt=now())
        report_not_scheduled = Q(next_report_date__isnull=True)

        q = Profile.objects.filter(report_due | report_not_scheduled)
        q = q.exclude(reports="off")
        profile = q.first()

        if profile is None:
            # No matching profiles found – nothing to do right now.
            return False

        # A sort of optimistic lock. Will try to update next_report_date,
        # and if does get modified, we're in drivers seat:
        qq = Profile.objects.filter(
            id=profile.id, next_report_date=profile.next_report_date
        )

        # Next report date is currently not scheduled: schedule it and move on.
        if profile.next_report_date is None:
            qq.update(next_report_date=profile.choose_next_report_date())
            return True

        num_updated = qq.update(next_report_date=profile.choose_next_report_date())
        if num_updated != 1:
            # next_report_date was already updated elsewhere, skipping
            return True

        if profile.send_report():
            self.stdout.write(self.tmpl % profile.user.email)
            # Pause before next report to avoid hitting sending quota
            self.pause()

        return True

    def handle_one_nag(self) -> bool:
        now_value = now()
        q = Profile.objects.filter(next_nag_date__lt=now_value)
        q = q.exclude(nag_period=NO_NAG)
        profile = q.first()

        if profile is None:
            return False

        qq = Profile.objects.filter(id=profile.id, next_nag_date=profile.next_nag_date)

        num_updated = qq.update(next_nag_date=now_value + profile.nag_period)
        if num_updated != 1:
            # next_rag_date was already updated elsewhere, skipping
            return True

        if profile.send_report(nag=True):
            self.stdout.write("Sent nag to %s" % profile.user.email)
            # Pause before next report to avoid hitting sending quota
            self.pause()
        else:
            profile.next_nag_date = None
            profile.save()

        return True

    def on_signal(self, signum: int, frame: FrameType | None) -> None:
        desc = signal.strsignal(signum)
        self.stdout.write(f"{desc}, finishing...\n")
        self.shutdown = True

    def handle(self, loop: bool, **options: Any) -> str:
        self.shutdown = False
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGINT, self.on_signal)

        self.stdout.write("sendreports is now running")
        while not self.shutdown:
            # Monthly reports
            while not self.shutdown and self.handle_one_report():
                pass

            # Daily and hourly nags
            while not self.shutdown and self.handle_one_nag():
                pass

            if not loop:
                break

            # Sleep for 60 seconds before looking for more work
            for i in range(0, 60):
                if not self.shutdown:
                    time.sleep(1)

        return "Done."
