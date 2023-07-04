from __future__ import annotations

import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from hc.accounts.models import Profile
from hc.lib import emails


class Command(BaseCommand):
    help = """Send warnings to accounts marked for deletion. """

    def pause(self):
        time.sleep(1)

    def handle(self, *args, **options):
        q = Profile.objects.order_by("id")
        q = q.filter(deletion_scheduled_date__gt=now())

        sent = 0
        for profile in q:
            self.stdout.write(f"Sending notice to {profile.user.email}")

            ctx = {
                "email": profile.user.email,
                "support_email": settings.SUPPORT_EMAIL,
                "deletion_scheduled_date": profile.deletion_scheduled_date,
            }
            emails.deletion_scheduled(profile.user.email, ctx)
            sent += 1

            # Throttle so we don't send too many emails at once:
            self.pause()

        return f"Done!\nNotices sent: {sent}\n"
