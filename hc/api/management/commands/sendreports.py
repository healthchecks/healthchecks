from __future__ import annotations

import signal
import time
from argparse import ArgumentParser
from types import FrameType
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
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
            self.stdout.write(f"Sent nag to {profile.user.email}")
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

    # Lock name / ID used to ensure only one sendreports instance runs at a time.
    # PostgreSQL uses a 64-bit integer advisory lock; MySQL uses a named string lock.
    # hex("hc_rep") = 0x68635F726570
    _PG_ADVISORY_LOCK_ID = 0x68635F726570
    _MYSQL_LOCK_NAME = "hc_sendreports"

    def _try_acquire_lock(self) -> bool:
        """Try to acquire a vendor-appropriate distributed lock.

        Returns True if the lock was acquired, False if another instance holds it.

        PostgreSQL: uses a session-level advisory lock (pg_try_advisory_lock).
          The lock is released automatically when the connection closes, so a
          crashed worker releases its lock without any cleanup step.

        MySQL: uses GET_LOCK() with a zero timeout (non-blocking). The lock is
          connection-scoped and is released automatically on disconnect, giving
          the same crash-safety guarantee as the PostgreSQL advisory lock.
        """
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.execute(
                    "SELECT pg_try_advisory_lock(%s)", [self._PG_ADVISORY_LOCK_ID]
                )
            else:
                # GET_LOCK returns 1=acquired, 0=timeout/not acquired, NULL=error
                cursor.execute(
                    "SELECT GET_LOCK(%s, 0)", [self._MYSQL_LOCK_NAME]
                )
            result = cursor.fetchone()[0]
            return bool(result)

    def _release_lock(self) -> None:
        """Release the distributed lock acquired by _try_acquire_lock."""
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.execute(
                    "SELECT pg_advisory_unlock(%s)", [self._PG_ADVISORY_LOCK_ID]
                )
            else:
                cursor.execute("SELECT RELEASE_LOCK(%s)", [self._MYSQL_LOCK_NAME])

    def handle(self, loop: bool, **options: Any) -> str:
        db = settings.DATABASES["default"]
        if "OPTIONS" in db and "application_name" in db["OPTIONS"]:
            db["OPTIONS"]["application_name"] = "sendreports"

        self.shutdown = False
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGINT, self.on_signal)

        # On PostgreSQL and MySQL, acquire a distributed lock so only one
        # sendreports instance runs at a time. Additional instances exit
        # immediately. If the primary crashes, the connection-scoped lock is
        # released automatically, allowing a standby to take over.
        # On SQLite the lock is skipped and the existing optimistic-lock pattern
        # inside handle_one_report/nag applies.
        use_distributed_lock = connection.vendor in ("postgresql", "mysql")
        if use_distributed_lock:
            if not self._try_acquire_lock():
                self.stdout.write(
                    "Another sendreports instance is already running (distributed "
                    "lock held). Exiting — this instance will become the active "
                    "worker automatically if the primary stops."
                )
                return "Done."

        self.stdout.write("sendreports is now running")
        try:
            while not self.shutdown:
                # The db connection may have timed out,
                # make sure we have a working db connection.
                # The if condition makes sure this does not run during tests.
                if not connection.in_atomic_block:
                    close_old_connections()

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
        finally:
            if use_distributed_lock:
                self._release_lock()

        return "Done."
