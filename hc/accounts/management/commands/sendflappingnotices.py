from __future__ import annotations

import time
from datetime import timedelta as td
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils.timezone import now

from hc.api.models import Check
from hc.lib import emails


class Command(BaseCommand):
    help = """Send notices about flapping checks."""

    def pause(self) -> None:
        time.sleep(1)

    def handle(self, **options: Any) -> str:
        q = Check.objects.only("name")
        q = q.filter(flip__created__gt=now() - td(hours=24))
        q = q.annotate(num_flips=Count("flip"))
        q = q.filter(num_flips__gt=200)
        q = q.order_by("-num_flips")

        sent = 0
        for check in q:
            email = check.project.owner.email
            self.stdout.write(
                f"[{check.num_flips}] Sending notice to {email} about '{check.name}'"
            )

            ctx = {
                "email": email,
                "check": check,
                "num_flips": check.num_flips,
                "support_email": settings.SUPPORT_EMAIL,
            }
            emails.flapping_notice(email, ctx)
            sent += 1

            # Throttle so we don't send too many emails at once:
            self.pause()

        return f"Done! Notices sent: {sent}\n"
